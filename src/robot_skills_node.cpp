#include <chrono>
#include <cmath>
#include <algorithm>
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
    if(velocity_<=0. || velocity_>0.2 || acceleration_<=0. || acceleration_>0.2 || approach_<0.03 || grasp_<0.05)
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
        try {
          if (state_["faulted"].get<bool>() || (scene_ && !scene_->healthy())) out->status="INVALID_STATE";
          else if (in->check_revision && in->expected_revision!=state_["revision"].get<uint64_t>()) out->status="STALE_STATE";
          else if (in->skill=="home" && in->object.empty() && in->zone.empty()) {
            out->status=home(); state_["revision"]=state_["revision"].get<uint64_t>()+1;
          } else if(in->skill=="pick" || in->skill=="place") {
            if(!scene_) out->status="INVALID_STATE";
            else if(!state_["object_locations"].contains(in->object)) out->status="INVALID_OBJECT";
            else if(in->skill=="pick" && !in->zone.empty()) out->status="INVALID_ZONE";
            else if(in->skill=="place" && in->zone!="zone_a" && in->zone!="zone_b" && in->zone!="zone_c") out->status="INVALID_ZONE";
            else {
              out->status=in->skill=="pick" ? pick(in->object) : place(in->object,in->zone);
              state_["revision"]=state_["revision"].get<uint64_t>()+1;
            }
          } else out->status="INVALID_SKILL";
        } catch(const std::exception& e) {out->status="FAILED";out->message=e.what();}
        if (out->status=="EXECUTION_FAILED" || out->status=="FAILED" || out->status=="GRASP_FAILED" || out->status=="SCENE_SYNC_FAILED" || out->status=="PLANNING_FAILED" || out->status=="STATE_UNAVAILABLE") state_["faulted"]=true;
        out->state_json=state_.dump();
        RCLCPP_INFO(node_->get_logger(),"%s: %s",in->skill.c_str(),out->status.c_str());
      });
  }
private:
  geometry_msgs::msg::Pose target(const geometry_msgs::msg::Pose& object,bool hover) {
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
  std::string approachMotion(const geometry_msgs::msg::Pose& object,moveit_msgs::msg::RobotTrajectory& descent) {
    auto current=group_.getCurrentState(2.0);if(!current)return "STATE_UNAVAILABLE";
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
    RCLCPP_INFO(node_->get_logger(),"place %s: above %s",object.c_str(),zone.c_str());
    moveit_msgs::msg::RobotTrajectory descent;
    auto result=approachMotion(pose,descent);if(result!="SUCCESS")return result;
    result=timedCartesian(descent);if(result!="SUCCESS")return result;
    if(!scene_->detach(object,pose))return "GRASP_FAILED";
    state_["held_object"]=nullptr;state_["object_locations"][object]=zone;
    RCLCPP_INFO(node_->get_logger(),"%s ATTACHED -> WORLD verified at %s",object.c_str(),zone.c_str());
    return cartesian(target(pose,true));
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
