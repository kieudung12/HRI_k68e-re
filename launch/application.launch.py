from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution

def generate_launch_description():
    return LaunchDescription([Node(package="ur3_llm_control", executable="robot_skills_node",
        output="screen",parameters=[
        PathJoinSubstitution([FindPackageShare("ur3_llm_control"),"config","robot_skills.yaml"]),
        {"use_sim_time":True, "scene_config":PathJoinSubstitution([FindPackageShare("ur3_llm_control"),"config","scene.yaml"])},
        PathJoinSubstitution([FindPackageShare("ur_moveit_config"),"config","kinematics.yaml"])]),
        Node(package="ur3_llm_control",executable="command_server",output="screen")])
