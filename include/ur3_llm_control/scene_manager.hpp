#pragma once
#include <atomic>
#include <mutex>
#include <thread>
#include <map>
#include <Eigen/Geometry>
#include <yaml-cpp/yaml.h>
#include <ignition/transport/Node.hh>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <rclcpp/rclcpp.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

// Explicit simulated grasp: collision attachment is authoritative; Gazebo
// static cube bodies follow TF via native Transport. No arm pose is teleported.
class SceneManager {
public:
  SceneManager(rclcpp::Node::SharedPtr io, const std::string& path, const std::string& frame, const std::string& eef);
  ~SceneManager();
  geometry_msgs::msg::Pose objectPose(const std::string& object) const;
  geometry_msgs::msg::Pose zonePose(const std::string& zone) const;
  geometry_msgs::msg::Pose toolPoseForObject(const geometry_msgs::msg::Pose& pose);
  bool resetObjects();
  bool attach(const std::string& object);
  bool detach(const std::string& object, const geometry_msgs::msg::Pose& pose);
  bool healthy() const {return healthy_;}
private:
  moveit_msgs::msg::CollisionObject box(const std::string&, const geometry_msgs::msg::Pose&, const std::vector<double>&) const;
  void spawn(const std::string&, const geometry_msgs::msg::Pose&, const std::vector<double>&, const std::string&, bool);
  void spawnZone(const std::string&, const geometry_msgs::msg::Pose&, char);
  bool setPose(const std::string&, const geometry_msgs::msg::Pose&);
  Eigen::Isometry3d toolTransform();
  void sync();
  rclcpp::Node::SharedPtr io_;
  std::string frame_,eef_,world_,held_;
  double size_,tray_size_,tray_elevation_,tray_wall_height_;
  std::map<std::string,geometry_msgs::msg::Pose> objects_,source_objects_,zones_;
  moveit::planning_interface::PlanningSceneInterface scene_;
  ignition::transport::Node gz_;
  tf2_ros::Buffer tf_;
  tf2_ros::TransformListener listener_;
  Eigen::Isometry3d offset_=Eigen::Isometry3d::Identity();
  std::mutex mutex_;
  std::atomic<bool> running_{true},healthy_{true};
  std::thread worker_;
};
