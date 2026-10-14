"""Spawn the official TurtleBot model at the room centre without a dock."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    model = LaunchConfiguration('model')
    world = LaunchConfiguration('world')
    sim_time = {'use_sim_time': 'true', 'namespace': ''}

    def include(package, filename, arguments):
        path = Path(get_package_share_directory(package)) / 'launch' / filename
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(path)),
            launch_arguments=arguments.items())

    return LaunchDescription([
        DeclareLaunchArgument('model', default_value='lite'),
        DeclareLaunchArgument('world', default_value='lec4_small_room'),
        include('turtlebot4_description', 'robot_description.launch.py',
                {**sim_time, 'model': model, 'robot_name': 'turtlebot4'}),
        Node(package='ros_ign_gazebo', executable='create', output='screen',
             arguments=['-world', world, '-name', 'turtlebot4',
                        '-x', '0', '-y', '0', '-z', '0', '-Y', '0',
                        '-topic', 'robot_description']),
        include('turtlebot4_ignition_bringup', 'ros_ign_bridge.launch.py',
                {**sim_time, 'model': model, 'world': world,
                 'robot_name': 'turtlebot4', 'dock_name': 'standard_dock'}),
        include('turtlebot4_ignition_bringup', 'turtlebot4_nodes.launch.py',
                {'model': model}),
        include('irobot_create_common_bringup', 'create3_nodes.launch.py',
                {'namespace': '', 'gazebo': 'ignition'}),
        include('irobot_create_ignition_bringup', 'create3_ignition_nodes.launch.py',
                {'robot_name': 'turtlebot4', 'dock_name': 'standard_dock'}),
        # These are the official sensor-frame rotations, not localization TF.
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='rplidar_stf', output='screen',
             arguments=['0', '0', '0', '0', '0', '0',
                        'rplidar_link', 'turtlebot4/rplidar_link/rplidar']),
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='camera_stf', output='screen',
             arguments=['0', '0', '0', '1.5707', '-1.5707', '0',
                        'oakd_rgb_camera_optical_frame',
                        'turtlebot4/oakd_rgb_camera_frame/rgbd_camera']),
    ])
