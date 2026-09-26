#include "ur3_llm_control/scene_manager.hpp"
#include <sstream>
#include <ignition/msgs/boolean.pb.h>
#include <ignition/msgs/entity_factory.pb.h>
#include <ignition/msgs/pose.pb.h>
#include <shape_msgs/msg/solid_primitive.hpp>
#include <moveit_msgs/msg/planning_scene.hpp>
using namespace std::chrono_literals;
namespace {
geometry_msgs::msg::Pose poseOf(const YAML::Node& p) {
  geometry_msgs::msg::Pose out;out.position.x=p[0].as<double>();out.position.y=p[1].as<double>();out.position.z=p[2].as<double>();out.orientation.w=1.;return out;
}
Eigen::Isometry3d eigen(const geometry_msgs::msg::Pose& p) {
  Eigen::Isometry3d t=Eigen::Isometry3d::Identity();
  t.translation()=Eigen::Vector3d(p.position.x,p.position.y,p.position.z);
  t.linear()=Eigen::Quaterniond(p.orientation.w,p.orientation.x,p.orientation.y,p.orientation.z).normalized().toRotationMatrix();return t;
}
geometry_msgs::msg::Pose poseOf(const Eigen::Isometry3d& t) {
  geometry_msgs::msg::Pose p;p.position.x=t.translation().x();p.position.y=t.translation().y();p.position.z=t.translation().z();
  Eigen::Quaterniond q(t.rotation());p.orientation.x=q.x();p.orientation.y=q.y();p.orientation.z=q.z();p.orientation.w=q.w();return p;
}
}
SceneManager::SceneManager(rclcpp::Node::SharedPtr io,const std::string& path,const std::string& frame,const std::string& eef)
:io_(io),frame_(frame),eef_(eef),tf_(io->get_clock()),listener_(tf_,io,false) {
  auto cfg=YAML::LoadFile(path);
  if (cfg["frame"].as<std::string>()!=frame_) throw std::runtime_error("Scene frame differs from actual planning frame");
  world_=cfg["world"].as<std::string>();size_=cfg["cube_size"].as<double>();
  for(const auto& entry:cfg["objects"]) objects_[entry.first.as<std::string>()]=poseOf(entry.second);
  for(const auto& entry:cfg["zones"]) zones_[entry.first.as<std::string>()]=poseOf(entry.second);
  if (!scene_.getObjects({"table","red_cube","yellow_cube","blue_cube"}).empty() || !scene_.getAttachedObjects().empty())
    throw std::runtime_error("Scene already initialized: restart the complete simulation to avoid resetting object state");
  auto table_pose=poseOf(cfg["table"]["center"]);
  auto table_size=cfg["table"]["size"].as<std::vector<double>>();
  std::vector<moveit_msgs::msg::CollisionObject> collisions{box("table",table_pose,table_size)};
  spawn("table",table_pose,table_size,"0.55 0.42 0.28 1",true);
  const std::map<std::string,std::string> colors{{"red_cube","0.9 0.1 0.1 1"},{"yellow_cube","0.95 0.8 0.05 1"},{"blue_cube","0.1 0.25 0.9 1"}};
  for(const auto& [name,p]:objects_) {
    collisions.push_back(box(name,p,{size_,size_,size_}));
    spawn(name,p,{size_,size_,size_},colors.at(name),true);
  }
  for(const auto& [name,p]:zones_) {
    auto marker=p;marker.position.z=table_pose.position.z+table_size[2]/2.+0.001;
    spawn(name,marker,{0.065,0.065,0.001},"0.1 0.8 0.3 0.6",false);
  }
  if(!scene_.applyCollisionObjects(collisions)) throw std::runtime_error("Cannot apply collision scene");
  for(const auto& [name,p]:objects_) if(!setPose(name,p)) throw std::runtime_error("Gazebo object synchronization failed at startup");
  worker_=std::thread([this]{sync();});
  RCLCPP_INFO(io_->get_logger(),"Scene initialized: table, 3 cubes, 3 zones; collision geometry applied");
}
SceneManager::~SceneManager(){running_=false;if(worker_.joinable())worker_.join();}
geometry_msgs::msg::Pose SceneManager::objectPose(const std::string& object) const{return objects_.at(object);}
geometry_msgs::msg::Pose SceneManager::zonePose(const std::string& zone) const{return zones_.at(zone);}
moveit_msgs::msg::CollisionObject SceneManager::box(const std::string& name,const geometry_msgs::msg::Pose& pose,const std::vector<double>& size) const {
  moveit_msgs::msg::CollisionObject out;out.header.frame_id=frame_;out.id=name;out.operation=out.ADD;
  shape_msgs::msg::SolidPrimitive primitive;primitive.type=primitive.BOX;primitive.dimensions.assign(size.begin(),size.end());
  out.primitives.push_back(primitive);out.primitive_poses.push_back(pose);return out;
}
void SceneManager::spawn(const std::string& name,const geometry_msgs::msg::Pose& pose,const std::vector<double>& size,const std::string& color,bool collision){
  std::ostringstream geometry;geometry<<"<geometry><box><size>"<<size[0]<<" "<<size[1]<<" "<<size[2]<<"</size></box></geometry>";
  std::ostringstream sdf;sdf<<"<sdf version='1.7'><model name='"<<name<<"'><static>true</static><pose>"<<pose.position.x<<" "<<pose.position.y<<" "<<pose.position.z<<" 0 0 0</pose><link name='body'>";
  if(collision)sdf<<"<collision name='collision'>"<<geometry.str()<<"</collision>";
  sdf<<"<visual name='visual'>"<<geometry.str()<<"<material><ambient>"<<color<<"</ambient><diffuse>"<<color<<"</diffuse></material></visual></link></model></sdf>";
  ignition::msgs::EntityFactory request;request.set_sdf(sdf.str());request.set_allow_renaming(false);
  ignition::msgs::Boolean response;bool result=false;
  if(!gz_.Request("/world/"+world_+"/create",request,5000,response,result)||!result||!response.data())throw std::runtime_error("Gazebo create failed for "+name+"; check IGN_PARTITION");
  std::this_thread::sleep_for(100ms);
}
bool SceneManager::setPose(const std::string& name,const geometry_msgs::msg::Pose& p){
  ignition::msgs::Pose request;request.set_name(name);
  request.mutable_position()->set_x(p.position.x);request.mutable_position()->set_y(p.position.y);request.mutable_position()->set_z(p.position.z);
  request.mutable_orientation()->set_x(p.orientation.x);request.mutable_orientation()->set_y(p.orientation.y);request.mutable_orientation()->set_z(p.orientation.z);request.mutable_orientation()->set_w(p.orientation.w);
  ignition::msgs::Boolean response;bool result=false;
  return gz_.Request("/world/"+world_+"/set_pose",request,500,response,result)&&result&&response.data();
}
Eigen::Isometry3d SceneManager::toolTransform(){
  const auto t=tf_.lookupTransform(frame_,eef_,tf2::TimePointZero);
  if((io_->now()-rclcpp::Time(t.header.stamp)).seconds()>1.)throw std::runtime_error("Tool TF is stale");
  geometry_msgs::msg::Pose p;p.position.x=t.transform.translation.x;p.position.y=t.transform.translation.y;p.position.z=t.transform.translation.z;p.orientation=t.transform.rotation;return eigen(p);
}
bool SceneManager::attach(const std::string& object){
  std::lock_guard<std::mutex> lock(mutex_);
  offset_=toolTransform().inverse()*eigen(objects_.at(object));
  moveit_msgs::msg::PlanningScene diff;diff.is_diff=true;diff.robot_state.is_diff=true;
  // MoveIt atomically removes the matching world object when attaching.
  // An extra world REMOVE would fail after that automatic removal.
  moveit_msgs::msg::AttachedCollisionObject attached;attached.link_name=eef_;attached.touch_links={eef_};
  attached.object=box(object,poseOf(offset_),{size_,size_,size_});attached.object.header.frame_id=eef_;
  diff.robot_state.attached_collision_objects.push_back(attached);
  if(!scene_.applyPlanningScene(diff))return false;
  held_=object;
  return scene_.getAttachedObjects({object}).count(object)==1 && scene_.getObjects({object}).empty();
}
bool SceneManager::detach(const std::string& object,const geometry_msgs::msg::Pose& pose){
  std::lock_guard<std::mutex> lock(mutex_);
  if(held_!=object)return false;
  moveit_msgs::msg::PlanningScene diff;diff.is_diff=true;diff.robot_state.is_diff=true;
  moveit_msgs::msg::AttachedCollisionObject remove;remove.link_name=eef_;remove.object.id=object;remove.object.operation=remove.object.REMOVE;
  diff.robot_state.attached_collision_objects.push_back(remove);diff.world.collision_objects.push_back(box(object,pose,{size_,size_,size_}));
  if(!scene_.applyPlanningScene(diff))return false;
  held_.clear();objects_[object]=pose;
  if(!setPose(object,pose)){healthy_=false;return false;}
  return scene_.getAttachedObjects({object}).empty() && scene_.getObjects({object}).count(object)==1;
}
void SceneManager::sync(){
  int failures=0;
  while(running_ && rclcpp::ok()) {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      if(!held_.empty()) {
        try {
          if(!setPose(held_,poseOf(toolTransform()*offset_)))throw std::runtime_error("Gazebo set_pose failed");
          failures=0;
        } catch(const std::exception& e){
          if(++failures>=3){healthy_=false;RCLCPP_ERROR(io_->get_logger(),"Scene synchronization failed: %s",e.what());}
        }
      }
    }
    std::this_thread::sleep_for(50ms);
  }
}
