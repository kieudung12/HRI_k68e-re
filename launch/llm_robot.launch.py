"""Proven UR simulation + MoveIt; application starts only after controller readiness."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, SetEnvironmentVariable, TimerAction, EmitEvent
from launch.events import Shutdown
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    share=FindPackageShare("ur3_llm_control")
    simulation=IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([
        FindPackageShare("ur_simulation_gz"),"launch","ur_sim_control.launch.py"])),
        launch_arguments={"ur_type":"ur3e","runtime_config_package":"ur3_llm_control",
         "controllers_file":"ur_controllers.yaml","initial_joint_controller":"joint_trajectory_controller",
         "gazebo_gui":LaunchConfiguration("gui"),"launch_rviz":"false",
         "world_file":LaunchConfiguration("world_file")}.items())
    moveit=IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([
        FindPackageShare("ur_moveit_config"),"launch","ur_moveit.launch.py"])),
        launch_arguments={"ur_type":"ur3e","use_sim_time":"true","launch_servo":"false",
                          "launch_rviz":LaunchConfiguration("rviz")}.items())
    ready=Node(package="ur3_llm_control",executable="controller_ready",output="screen")
    app=IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([
        share,"launch","application.launch.py"])),condition=IfCondition(LaunchConfiguration("application")))
    def after_ready(event,context):
        return [app] if event.returncode==0 else [EmitEvent(event=Shutdown(reason="Controller readiness failed"))]
    # Same name and no renaming: a delayed retry cannot create a second robot.
    retry=Node(package="ros_gz_sim",executable="create",output="log",
        arguments=["-topic","robot_description","-name","ur","-allow_renaming=false"])
    guard=Node(package="ur3_llm_control",executable="spawn_guard",output="screen")
    def after_guard(event,context):
        return [retry] if event.returncode==2 else []
    return LaunchDescription([
        DeclareLaunchArgument("gui",default_value="false"),
        DeclareLaunchArgument("rviz",default_value="false"),
        DeclareLaunchArgument("application",default_value="true"),
        DeclareLaunchArgument("world_file",default_value=PathJoinSubstitution([share,"worlds","assignment2.sdf"])),
        DeclareLaunchArgument("ign_partition",default_value="ur3_assignment2"),
        SetEnvironmentVariable("IGN_PARTITION",LaunchConfiguration("ign_partition")),
        simulation,moveit,RegisterEventHandler(OnProcessExit(target_action=ready,on_exit=after_ready)),
        RegisterEventHandler(OnProcessExit(target_action=guard,on_exit=after_guard)),
        TimerAction(period=15.,actions=[ready]),TimerAction(period=10.,actions=[guard])])
