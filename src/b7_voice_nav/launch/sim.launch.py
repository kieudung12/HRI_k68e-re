"""B7 world + official TurtleBot 4 packages, independently of other lab workspaces."""
import os
from pathlib import Path

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription,
                            SetEnvironmentVariable, Shutdown)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory('b7_voice_nav'))
    executable = Path(get_package_prefix('b7_voice_nav')) / 'lib/b7_voice_nav/gazebo_server'
    model = LaunchConfiguration('model')
    common = {'use_sim_time': 'true', 'namespace': ''}

    def include(package, filename, arguments):
        path = Path(get_package_share_directory(package)) / 'launch' / filename
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(str(path)),
                                        launch_arguments=arguments.items())

    resources = [str(share / 'worlds'), '/opt/ros/humble/share']
    gui_paths = [get_package_share_directory(p) + '/lib' for p in
                 ['turtlebot4_ignition_gui_plugins', 'irobot_create_ignition_plugins']]
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value='lite', choices=['lite', 'standard']),
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false']),
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', os.pathsep.join(resources)),
        SetEnvironmentVariable('IGN_GUI_PLUGIN_PATH', os.pathsep.join(gui_paths)),
        SetEnvironmentVariable('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', os.environ.get('LD_LIBRARY_PATH', '')),
        ExecuteProcess(cmd=[str(executable), str(share / 'worlds/b7_campus.sdf')],
                       output='screen', on_exit=Shutdown(reason='B7 Gazebo server ended')),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='clock_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock']),
        include('turtlebot4_description', 'robot_description.launch.py',
                {**common, 'model': model, 'robot_name': 'turtlebot4'}),
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-world', 'b7_campus', '-name', 'turtlebot4', '-topic',
                        'robot_description', '-x', '0', '-y', '0', '-z', '0', '-Y', '0']),
        include('turtlebot4_ignition_bringup', 'ros_ign_bridge.launch.py',
                {**common, 'model': model, 'world': 'b7_campus',
                 'robot_name': 'turtlebot4', 'dock_name': 'standard_dock'}),
        include('turtlebot4_ignition_bringup', 'turtlebot4_nodes.launch.py', {'model': model}),
        include('irobot_create_common_bringup', 'create3_nodes.launch.py',
                {'namespace': '', 'gazebo': 'ignition'}),
        include('irobot_create_ignition_bringup', 'create3_ignition_nodes.launch.py',
                {'robot_name': 'turtlebot4', 'dock_name': 'standard_dock'}),
        Node(package='tf2_ros', executable='static_transform_publisher', name='lidar_frame',
             arguments=['0', '0', '0', '0', '0', '0',
                        'rplidar_link', 'turtlebot4/rplidar_link/rplidar']),
        Node(package='tf2_ros', executable='static_transform_publisher', name='camera_frame',
             arguments=['0', '0', '0', '1.5707', '-1.5707', '0',
                        'oakd_rgb_camera_optical_frame', 'turtlebot4/oakd_rgb_camera_frame/rgbd_camera']),
        Node(package='b7_voice_nav', executable='gazebo_gui', output='screen',
             condition=IfCondition(LaunchConfiguration('gui'))),
    ])
