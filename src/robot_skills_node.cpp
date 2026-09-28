#include <chrono>
#include <cmath>
#include <algorithm>
#include <array>
#include <limits>
#include <utility>
#include <moveit/trajectory_processing/iterative_time_parameterization.h>
#include <moveit/robot_trajectory/robot_trajectory.h>
#include <moveit/robot_state/conversions.h>
#include <moveit_msgs/srv/get_position_ik.hpp>
#include <memory>
#include <string>
#include <thread>
#include <nlohmann/json.hpp>
#include <rclcpp/rclcpp.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include "ur3_llm_control/srv/execute_skill.hpp"
#include "ur3_llm_control/srv/reset_scene.hpp"
#include "ur3_llm_control/scene_manager.hpp"
#include "ur3_llm_control/srv/get_state.hpp"

using MoveGroup = moveit::planning_interface::MoveGroupInterface;
using json = nlohmann::json;
using namespace std::chrono_literals;

template<class T> T param(const rclcpp::Node::SharedPtr& n, const std::string& key, const T& value) {
  if (!n->has_parameter(key)) n->declare_parameter<T>(key, value);
  return n->get_parameter(key).get_value<T>();
}

class RobotSkills {
public:
  RobotSkills(rclcpp::Node::SharedPtr node, rclcpp::Node::SharedPtr io)
  : node_(node), group_(io, param<std::string>(node,"planning_group","ur_manipulator")) {
    ik_client_=io->create_client<moveit_msgs::srv::GetPositionIK>("/compute_ik");
    group_.setPlanningTime(10.0);
    group_.setNumPlanningAttempts(10);
    group_.setMaxVelocityScalingFactor(param<double>(node,"velocity_scaling",0.05));
    group_.setMaxAccelerationScalingFactor(param<double>(node,"acceleration_scaling",0.05));
    velocity_=param<double>(node,"velocity_scaling",0.05);
    acceleration_=param<double>(node,"acceleration_scaling",0.05);
    approach_=param<double>(node,"approach_height",0.08);
    grasp_=param<double>(node,"grasp_offset",0.10);
    const auto q=param<std::vector<double>>(node,"tool_quaternion",{1.,0.,0.,0.});
    if(q.size()!=4 || std::abs(q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3]-1.)>0.001)
      throw std::runtime_error("Tool quaternion must have unit length");
    orientation_.x=q[0];orientation_.y=q[1];orientation_.z=q[2];orientation_.w=q[3];
    if(velocity_<=0. || velocity_>0.3 || acceleration_<=0. || acceleration_>0.3 || approach_<0.03 || grasp_<0.05)
      throw std::runtime_error("Unsafe skill configuration");
    home_ = param<std::string>(node,"home_target","up");
    eef_ = group_.getEndEffectorLink();
    if (eef_.empty()) throw std::runtime_error("MoveGroup has no end-effector link");
    RCLCPP_INFO(node_->get_logger(),"Planning frame=%s; actual end-effector=%s",group_.getPlanningFrame().c_str(),eef_.c_str());
    if (!group_.getCurrentState(15.0)) throw std::runtime_error("No fresh robot state");
    for (const auto& joint : group_.getJointNames()) RCLCPP_INFO(node_->get_logger(),"Joint: %s",joint.c_str());
    const auto scene_path=param<std::string>(node,"scene_config","");
    if(!scene_path.empty()) scene_=std::make_unique<SceneManager>(io,scene_path,group_.getPlanningFrame(),eef_);
    state_ = {{"held_object",nullptr},{"object_locations",{{"red_cube","source"},{"yellow_cube","source"},{"blue_cube","source"}}},{"revision",0},{"faulted",false}};
    state_["planning_frame"]=group_.getPlanningFrame();state_["end_effector_link"]=eef_;
    get_ = node_->create_service<ur3_llm_control::srv::GetState>("/robot_skills/state",
      [this](const std::shared_ptr<ur3_llm_control::srv::GetState::Request>,std::shared_ptr<ur3_llm_control::srv::GetState::Response> out){out->state_json=state_.dump();});
    run_ = node_->create_service<ur3_llm_control::srv::ExecuteSkill>("/robot_skills/execute",
      [this](const std::shared_ptr<ur3_llm_control::srv::ExecuteSkill::Request> in,std::shared_ptr<ur3_llm_control::srv::ExecuteSkill::Response> out){
        bool accepted=false;
        try {
          if (state_["faulted"].get<bool>()) out->status="INVALID_STATE";
          else if (scene_ && !scene_->healthy()) out->status="SCENE_SYNC_FAILED";
          else if (in->check_revision && in->expected_revision!=state_["revision"].get<uint64_t>()) out->status="STALE_STATE";
          else if (in->skill=="home" && in->object.empty() && in->zone.empty()) {
            accepted=true; out->status=home();
          } else if(in->skill=="pick" || in->skill=="place") {
            if(!scene_) out->status="INVALID_STATE";
            else if(!state_["object_locations"].contains(in->object)) out->status="INVALID_OBJECT";
            else if(in->skill=="pick" && !in->zone.empty()) out->status="INVALID_ZONE";
            else if(in->skill=="place" && in->zone!="zone_a" && in->zone!="zone_b" && in->zone!="zone_c") out->status="INVALID_ZONE";
            else {
              accepted=true; out->status=in->skill=="pick" ? pick(in->object) : place(in->object,in->zone);
            }
          } else out->status="INVALID_SKILL";
        } catch(const std::exception& e) {out->status="FAILED";out->message=e.what();}
        const bool fault_status=out->status=="EXECUTION_FAILED" || out->status=="FAILED" || out->status=="GRASP_FAILED" || out->status=="SCENE_SYNC_FAILED" || out->status=="PLANNING_FAILED" || out->status=="STATE_UNAVAILABLE";
        const bool new_fault=fault_status && !state_["faulted"].get<bool>();
        if(fault_status) state_["faulted"]=true;
        // Revision versions authoritative execution state: successful skills (home
        // included, because robot pose changed) and first transition into faulted.
        // Invalid/stale requests never advance it; partial failures fail closed.
        if((accepted && out->status=="SUCCESS") || new_fault)
          state_["revision"]=state_["revision"].get<uint64_t>()+1;
        out->state_json=state_.dump();
        RCLCPP_INFO(node_->get_logger(),"%s: %s",in->skill.c_str(),out->status.c_str());
      });
    reset_ = node_->create_service<ur3_llm_control::srv::ResetScene>("/robot_skills/reset_scene",
      [this](const std::shared_ptr<ur3_llm_control::srv::ResetScene::Request>,
             std::shared_ptr<ur3_llm_control::srv::ResetScene::Response> out) {
        const bool was_faulted=state_["faulted"].get<bool>();
        bool home_completed=false;
        try {
          if(was_faulted) out->message="Robot state is faulted; restart and inspect the simulation before resetting";
          else if(!scene_) out->message="Scene manager is unavailable";
          else if(!scene_->healthy()) out->message="Scene synchronization is unhealthy; restart and inspect the simulation";
          else if(!state_["held_object"].is_null()) out->message="Robot is holding an object; complete placement before resetting";
          else {
            const auto home_status=home();
            if(home_status!="SUCCESS") {
              out->message="Could not move robot to home: "+home_status;
              if(home_status=="EXECUTION_FAILED" || home_status=="STATE_UNAVAILABLE") state_["faulted"]=true;
            } else {
              home_completed=true;
              if(!scene_->resetObjects()) {
                out->message="Could not safely return all cubes to their source positions";
                if(!scene_->healthy()) state_["faulted"]=true;
              } else {
                for(auto& item:state_["object_locations"].items()) item.value()="source";
                state_["held_object"]=nullptr;
                out->success=true;
                out->message="Robot moved home; all cubes returned to their original positions.";
              }
            }
          }
        } catch(const std::exception& e) {
          out->message=std::string("Reset failed: ")+e.what();
          state_["faulted"]=true;
        }
        if(home_completed || out->success || (!was_faulted && state_["faulted"].get<bool>()))
          state_["revision"]=state_["revision"].get<uint64_t>()+1;
        out->state_json=state_.dump();
        RCLCPP_INFO(node_->get_logger(),"reset_scene: %s",out->message.c_str());
      });
  }
private:
  geometry_msgs::msg::Pose target(const geometry_msgs::msg::Pose& object,bool hover) {
    if(!state_["held_object"].is_null()) {
      auto pose=scene_->toolPoseForObject(object);
      if(hover)pose.position.z+=approach_;
      return pose;
    }
    auto pose=object;pose.position.z+=grasp_+(hover?approach_:0.);pose.orientation=orientation_;return pose;
  }
  std::string execute(const MoveGroup::Plan& plan) {
    if(scene_ && !scene_->healthy()) return "SCENE_SYNC_FAILED";
    const auto result=group_.execute(plan);
    if(scene_ && !scene_->healthy()) return "SCENE_SYNC_FAILED";
    return result==moveit::core::MoveItErrorCode::SUCCESS ? "SUCCESS" : "EXECUTION_FAILED";
  }
  void startState(const moveit::core::RobotState& state) {
    moveit_msgs::msg::RobotState msg;
    moveit::core::robotStateToRobotStateMsg(state,msg);
    // Retain the authoritative Planning Scene attachments when updating joints.
    msg.is_diff=true;group_.setStartState(msg);
  }
  bool smallJumps(const moveit_msgs::msg::RobotTrajectory& trajectory) {
    const auto& points=trajectory.joint_trajectory.points;
    if(points.empty())return false;
    for(size_t i=1;i<points.size();++i)
      for(size_t j=0;j<points[i].positions.size();++j)
        if(std::abs(points[i].positions[j]-points[i-1].positions[j])>0.5)return false;
    return true;
  }
  bool joins(const moveit_msgs::msg::RobotTrajectory& first,
             const moveit_msgs::msg::RobotTrajectory& second) {
    if(first.joint_trajectory.points.empty() || second.joint_trajectory.points.empty() ||
       first.joint_trajectory.joint_names!=second.joint_trajectory.joint_names) return false;
    const auto& a=first.joint_trajectory.points.back().positions;
    const auto& b=second.joint_trajectory.points.front().positions;
    if(a.size()!=b.size()) return false;
    for(size_t j=0;j<a.size();++j) if(std::abs(a[j]-b[j])>0.5) return false;
    return true;
  }
  bool optimizedCarryRoute(const geometry_msgs::msg::Pose& object,
                           const moveit::core::RobotState& current,
                           moveit_msgs::msg::RobotTrajectory& transit,
                           moveit_msgs::msg::RobotTrajectory& descent) {
    const auto measured=group_.getCurrentPose(eef_).pose;
    auto hover=target(object,true);

    // Search from a direct, level transfer outward in 1 cm clearance steps.
    // Each candidate is collision checked as a complete Cartesian path. The
    // first valid route has the least vertical detour in this scene and keeps
    // the carried cube low while travelling from pickup hover to drop hover.
    constexpr double clearance_step=0.01;
    constexpr double max_extra_clearance=0.15;
    for(int level=0;level<=15;++level) {
      const double clearance=level*clearance_step;
      std::vector<geometry_msgs::msg::Pose> waypoints;
      double geometric_length=0.;
      if(level==0) {
        waypoints.push_back(hover);
        geometric_length=std::sqrt(
          std::pow(hover.position.x-measured.position.x,2)+
          std::pow(hover.position.y-measured.position.y,2)+
          std::pow(hover.position.z-measured.position.z,2));
      } else {
        const double travel_z=std::max(measured.position.z,hover.position.z)+clearance;
        auto lift=measured;lift.position.z=travel_z;lift.orientation=orientation_;
        auto cross=hover;cross.position.z=travel_z;
        waypoints={lift,cross,hover};
        geometric_length=std::abs(travel_z-measured.position.z)+
          std::hypot(hover.position.x-measured.position.x,hover.position.y-measured.position.y)+
          std::abs(travel_z-hover.position.z);
      }

      startState(current);
      moveit_msgs::msg::RobotTrajectory candidate_transit;
      const double fraction=group_.computeCartesianPath(waypoints,0.005,0.,candidate_transit,true);
      if(fraction<0.999999 || !smallJumps(candidate_transit) || candidate_transit.joint_trajectory.points.empty())
        continue;

      auto hover_state=current;
      const auto& endpoint=candidate_transit.joint_trajectory.points.back();
      for(size_t j=0;j<candidate_transit.joint_trajectory.joint_names.size();++j)
        hover_state.setVariablePosition(candidate_transit.joint_trajectory.joint_names[j],endpoint.positions[j]);
      hover_state.update();
      startState(hover_state);
      moveit_msgs::msg::RobotTrajectory candidate_descent;
      const double down_fraction=group_.computeCartesianPath({target(object,false)},0.005,0.,candidate_descent,true);
      startState(current);
      if(down_fraction<0.999999 || !smallJumps(candidate_descent) || !joins(candidate_transit,candidate_descent))
        continue;

      transit=std::move(candidate_transit);
      descent=std::move(candidate_descent);
      RCLCPP_INFO(node_->get_logger(),
        "Optimized carry route selected: clearance %.2f m, Cartesian length %.3f m",
        clearance,geometric_length);
      return true;
    }
    startState(current);
    RCLCPP_WARN(node_->get_logger(),
      "No direct collision-free carry route found within %.2f m extra clearance; using guarded fallback",
      max_extra_clearance);
    return false;
  }
  bool plannedCarryRoute(const geometry_msgs::msg::Pose& object,
                         const moveit::core::RobotState& current,
                         moveit_msgs::msg::RobotTrajectory& transit,
                         moveit_msgs::msg::RobotTrajectory& descent) {
    // A Cartesian line can be blocked by a shoulder/elbow collision even when
    // both end poses are valid. Let MoveIt find a collision-free joint-space
    // route to the hover pose, then independently validate the short vertical
    // placement segment before moving the robot.
    auto hover=target(object,true);
    double best_length=std::numeric_limits<double>::infinity();
    moveit_msgs::msg::RobotTrajectory best_transit,best_descent;
    constexpr int candidates=4;
    for(int trial=0;trial<candidates;++trial) {
      startState(current);
      group_.setPlanningTime(2.0);
      group_.setPoseTarget(hover,eef_);
      MoveGroup::Plan plan;
      const auto result=group_.plan(plan);
      group_.clearPoseTargets();
      if(result!=moveit::core::MoveItErrorCode::SUCCESS ||
         plan.trajectory_.joint_trajectory.points.empty()) continue;

      const auto& points=plan.trajectory_.joint_trajectory.points;
      double length=0.;
      for(size_t i=1;i<points.size();++i)
        for(size_t j=0;j<points[i].positions.size();++j)
          length+=std::abs(points[i].positions[j]-points[i-1].positions[j]);

      auto hover_state=current;
      const auto& endpoint=points.back();
      for(size_t j=0;j<plan.trajectory_.joint_trajectory.joint_names.size();++j)
        hover_state.setVariablePosition(plan.trajectory_.joint_trajectory.joint_names[j],endpoint.positions[j]);
      hover_state.update();
      startState(hover_state);
      moveit_msgs::msg::RobotTrajectory candidate_descent;
      const double fraction=group_.computeCartesianPath(
        {target(object,false)},0.005,0.,candidate_descent,true);
      if(fraction<0.999999 || !smallJumps(candidate_descent) ||
         !joins(plan.trajectory_,candidate_descent)) continue;
      if(length<best_length) {
        best_length=length;
        best_transit=plan.trajectory_;
        best_descent=std::move(candidate_descent);
      }
    }
    startState(current);
    if(best_transit.joint_trajectory.points.empty()) return false;
    transit=std::move(best_transit);
    descent=std::move(best_descent);
    RCLCPP_INFO(node_->get_logger(),
      "Collision-free carry route selected by MoveIt: joint path length %.3f rad",
      best_length);
    return true;
  }
  std::string approachMotion(const geometry_msgs::msg::Pose& object,moveit_msgs::msg::RobotTrajectory& descent) {
    auto current=group_.getCurrentState(2.0);if(!current)return "STATE_UNAVAILABLE";
    moveit_msgs::msg::RobotTrajectory direct;
    if(optimizedCarryRoute(object,*current,direct,descent))return timedCartesian(direct);
    if(!state_["held_object"].is_null()) {
      moveit_msgs::msg::RobotTrajectory transit;
      if(plannedCarryRoute(object,*current,transit,descent))
        return timedCartesian(transit);
      return "PLANNING_FAILED";
    }
    if(!ik_client_->wait_for_service(5s))return "PLANNING_FAILED";
    auto seed=*current;
    for(int trial=0;trial<16;++trial) {
      if(trial)seed.setToRandomPositions(seed.getJointModelGroup(group_.getName()));
      auto request=std::make_shared<moveit_msgs::srv::GetPositionIK::Request>();
      auto& ik=request->ik_request;ik.group_name=group_.getName();ik.ik_link_name=eef_;
      ik.avoid_collisions=true;ik.timeout.sec=1;
      moveit::core::robotStateToRobotStateMsg(seed,ik.robot_state);ik.robot_state.is_diff=true;
      ik.pose_stamped.header.frame_id=group_.getPlanningFrame();ik.pose_stamped.pose=target(object,false);
      auto future=ik_client_->async_send_request(request);
      if(future.wait_for(3s)!=std::future_status::ready)return "PLANNING_FAILED";
      const auto response=future.get();
      if(response->error_code.val!=moveit_msgs::msg::MoveItErrorCodes::SUCCESS)continue;
      auto solved=response->solution;solved.is_diff=true;group_.setStartState(solved);
      moveit_msgs::msg::RobotTrajectory reverse;
      const double fraction=group_.computeCartesianPath({target(object,true)},0.005,0.,reverse,true);
      if(fraction<0.999999 || !smallJumps(reverse))continue;
      // A fully checked grasp -> hover path gives a compatible hover IK branch.
      // Its reversal is the descent; retime before execution.
      const auto now=group_.getCurrentJointValues();
      const auto names=group_.getJointNames();
      std::map<std::string,double> goal;
      for(size_t j=0;j<reverse.joint_trajectory.joint_names.size();++j) {
        const auto& name=reverse.joint_trajectory.joint_names[j];
        const auto index=std::distance(names.begin(),std::find(names.begin(),names.end(),name));
        if(index>=static_cast<long>(now.size()))return "PLANNING_FAILED";
        const double old=reverse.joint_trajectory.points.back().positions[j];double near=old;
        while(near-now[index]>M_PI)near-=2*M_PI;
        while(near-now[index]<-M_PI)near+=2*M_PI;
        for(auto& point:reverse.joint_trajectory.points)point.positions[j]+=near-old;
        goal[name]=near;
      }
      startState(*current);
      // Prefer a staged Cartesian transit: lift vertically, translate over
      // the target, rotate to the downward grasp orientation, then descend.
      // Connecting the descent to the transit endpoint avoids changing to a
      // different wrist IK branch (and taking an unnecessarily long OMPL route).
      moveit_msgs::msg::RobotTrajectory transit;
      const auto measured_pose=group_.getCurrentPose(eef_).pose;
      auto high=target(object,true);
      // Keep the travel plane tied to the target, with only the configured
      // clearance above the hover pose. Using max(current_z, target_z) made a
      // return from the high SRDF home pose carry the cube high across the
      // whole workspace.
      high.position.z+=approach_;
      high.orientation=measured_pose.orientation;
      auto lift=measured_pose;
      lift.position.z=high.position.z;
      auto rotate=high;
      rotate.orientation=orientation_;
      const double transit_fraction=group_.computeCartesianPath({lift,high,rotate,target(object,true)},0.005,0.,transit,true);
      bool staged=false;
      if(transit_fraction>=0.999999 && smallJumps(transit) && !transit.joint_trajectory.points.empty()) {
        auto hover_state=*current;
        const auto& endpoint=transit.joint_trajectory.points.back();
        for(size_t j=0;j<transit.joint_trajectory.joint_names.size();++j)
          hover_state.setVariablePosition(transit.joint_trajectory.joint_names[j],endpoint.positions[j]);
        hover_state.update();
        startState(hover_state);
        moveit_msgs::msg::RobotTrajectory candidate_descent;
        const double descent_fraction=group_.computeCartesianPath({target(object,false)},0.005,0.,candidate_descent,true);
        startState(*current);
        if(descent_fraction>=0.999999 && smallJumps(candidate_descent) && joins(transit,candidate_descent)) {
          descent=std::move(candidate_descent);
          staged=true;
        }
      }
      if(staged) {
        RCLCPP_INFO(node_->get_logger(),"Staged Cartesian route selected: lift, straight traverse, rotate, descend (candidate %d)",trial+1);
        return timedCartesian(transit);
      }
      if(!group_.setJointValueTarget(goal))continue;
      MoveGroup::Plan plan;
      if(group_.plan(plan)!=moveit::core::MoveItErrorCode::SUCCESS)continue;
      descent=reverse;
      std::reverse(descent.joint_trajectory.points.begin(),descent.joint_trajectory.points.end());
      for(auto& point:descent.joint_trajectory.points){point.time_from_start.sec=0;point.time_from_start.nanosec=0;point.velocities.clear();point.accelerations.clear();}
      RCLCPP_INFO(node_->get_logger(),"Full approach prevalidated, candidate %d",trial+1);
      return execute(plan);
    }
    return "PLANNING_FAILED";
  }
  std::string timedCartesian(moveit_msgs::msg::RobotTrajectory trajectory) {
    std::this_thread::sleep_for(300ms);
    auto current=group_.getCurrentState(2.0);if(!current)return "STATE_UNAVAILABLE";
    if(trajectory.joint_trajectory.points.empty())return "PLANNING_FAILED";
    // KDL/Cartesian responses may encode an equivalent wrist angle +/- 2*pi.
    // Unwrap every point from the measured start, including the first point.
    std::vector<double> previous;
    for(const auto& name:trajectory.joint_trajectory.joint_names)
      previous.push_back(current->getVariablePosition(name));
    for(auto& point:trajectory.joint_trajectory.points) {
      for(size_t j=0;j<point.positions.size();++j) {
        while(point.positions[j]-previous[j]>M_PI)point.positions[j]-=2*M_PI;
        while(point.positions[j]-previous[j]<-M_PI)point.positions[j]+=2*M_PI;
        if(std::abs(point.positions[j]-previous[j])>0.5)return "PLANNING_FAILED";
        previous[j]=point.positions[j];
      }
    }
    if(!smallJumps(trajectory))return "PLANNING_FAILED";
    robot_trajectory::RobotTrajectory timed(group_.getRobotModel(),group_.getName());
    timed.setRobotTrajectoryMsg(*current,trajectory);
    trajectory_processing::IterativeParabolicTimeParameterization retime;
    if(!retime.computeTimeStamps(timed,velocity_,acceleration_))return "PLANNING_FAILED";
    MoveGroup::Plan plan;timed.getRobotTrajectoryMsg(plan.trajectory_);
    return execute(plan);
  }
  std::string cartesian(const geometry_msgs::msg::Pose& pose) {
    std::this_thread::sleep_for(300ms);
    auto current=group_.getCurrentState(2.0);if(!current)return "INVALID_STATE";
    startState(*current);
    moveit_msgs::msg::RobotTrajectory trajectory;
    double fraction=group_.computeCartesianPath({pose},0.005,0.0,trajectory,true);
    RCLCPP_INFO(node_->get_logger(),"Collision-checked Cartesian fraction %.3f",fraction);
    if(fraction<0.999999 || trajectory.joint_trajectory.points.empty())return "PLANNING_FAILED";
    return timedCartesian(trajectory);
  }

  std::string pick(const std::string& object) {
    if(!state_["held_object"].is_null())return "INVALID_STATE";
    const auto pose=scene_->objectPose(object);
    RCLCPP_INFO(node_->get_logger(),"pick %s: above object",object.c_str());
    moveit_msgs::msg::RobotTrajectory descent;
    auto result=approachMotion(pose,descent);if(result!="SUCCESS")return result;
    result=timedCartesian(descent);if(result!="SUCCESS")return result;
    if(!scene_->attach(object))return "GRASP_FAILED";
    state_["held_object"]=object;state_["object_locations"][object]="held";
    RCLCPP_INFO(node_->get_logger(),"%s WORLD -> ATTACHED verified",object.c_str());
    return cartesian(target(pose,true));
  }
  std::string place(const std::string& object,const std::string& zone) {
    if(state_["held_object"]!=object)return "INVALID_STATE";
    for(const auto& item:state_["object_locations"].items())if(item.value()==zone)return "INVALID_STATE";
    const auto pose=scene_->zonePose(zone);
    moveit_msgs::msg::RobotTrajectory descent;
    auto result=approachMotion(pose,descent);if(result!="SUCCESS")return result;
    result=timedCartesian(descent);if(result!="SUCCESS")return result;
    // Compute retreat with the measured attachment transform before release.
    const auto retreat=target(pose,true);
    if(!scene_->detach(object,pose))return "GRASP_FAILED";
    state_["held_object"]=nullptr;state_["object_locations"][object]=zone;
    RCLCPP_INFO(node_->get_logger(),"%s ATTACHED -> WORLD verified inside %s",object.c_str(),zone.c_str());
    return cartesian(retreat);
  }
  std::string home() {
    if (!state_["held_object"].is_null()) return "INVALID_STATE";
    auto current=group_.getCurrentState(2.0);
    if (!current) return "INVALID_STATE";
    startState(*current);
    if (!group_.setNamedTarget(home_)) return "PLANNING_FAILED";
    MoveGroup::Plan plan;
    if (group_.plan(plan)!=moveit::core::MoveItErrorCode::SUCCESS) return "PLANNING_FAILED";
    return execute(plan);
  }
  rclcpp::Node::SharedPtr node_;
  MoveGroup group_;
  rclcpp::Client<moveit_msgs::srv::GetPositionIK>::SharedPtr ik_client_;
  std::string home_,eef_;
  double velocity_,acceleration_,approach_,grasp_;
  geometry_msgs::msg::Quaternion orientation_;
  json state_;
  std::unique_ptr<SceneManager> scene_;
  rclcpp::Service<ur3_llm_control::srv::ExecuteSkill>::SharedPtr run_;
  rclcpp::Service<ur3_llm_control::srv::ResetScene>::SharedPtr reset_;
  rclcpp::Service<ur3_llm_control::srv::GetState>::SharedPtr get_;
};

int main(int argc,char** argv) {
  rclcpp::init(argc,argv);
  rclcpp::NodeOptions options;
  options.automatically_declare_parameters_from_overrides(true);
  auto node=std::make_shared<rclcpp::Node>("robot_skills",options);
  auto io=std::make_shared<rclcpp::Node>("skill_moveit_client",options);
  param<bool>(node,"use_sim_time",true); param<bool>(io,"use_sim_time",true);
  // MoveIt callbacks must continue while the serialized skill service blocks.
  rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),4);
  executor.add_node(node);executor.add_node(io);
  std::thread spinner([&]{executor.spin();});
  int result=0;
  try {RobotSkills skills(node,io); spinner.join();}
  catch(const std::exception& e) {
    RCLCPP_ERROR(node->get_logger(),"Initialization failed: %s",e.what());
    executor.cancel(); spinner.join(); result=1;
  }
  rclcpp::shutdown(); return result;
}
