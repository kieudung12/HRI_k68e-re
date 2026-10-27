from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.actions import Node


def generate_launch_description():
    lec4_sim = get_package_share_directory('lec4_robot_lab') + '/launch/sim.launch.py'
    return LaunchDescription([
        DeclareLaunchArgument('camera', default_value='0'),
        DeclareLaunchArgument('stable_frames', default_value='3'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('world', default_value='lec4_small_room'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lec4_sim),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'model': 'lite',
                'gui': LaunchConfiguration('gui'),
                'rviz': 'false',
            }.items(),
        ),
        Node(
            package='b6_gesture_control', executable='robot_behavior_node',
            name='robot_behavior_node', output='screen',
        ),
        Node(
            package='b6_gesture_control', executable='gesture_recognition_node',
            name='gesture_recognition_node', output='screen',
            parameters=[{
                'camera_index': ParameterValue(
                    LaunchConfiguration('camera'), value_type=int),
                'stable_frames': ParameterValue(
                    LaunchConfiguration('stable_frames'), value_type=int),
            }],
        ),
    ])
