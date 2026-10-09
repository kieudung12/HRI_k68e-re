from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    turtlebot_launch = PathJoinSubstitution([
        FindPackageShare('turtlebot4_ignition_bringup'),
        'launch',
        'turtlebot4_ignition.launch.py',
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value='maze',
            description='Official TurtleBot 4 Humble world name',
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='false',
            choices=['true', 'false'],
            description='Start the official TurtleBot 4 RViz configuration',
        ),
        DeclareLaunchArgument(
            'model',
            default_value='standard',
            choices=['standard', 'lite'],
        ),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(turtlebot_launch),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'rviz': LaunchConfiguration('rviz'),
                'model': LaunchConfiguration('model'),
                'x': LaunchConfiguration('x'),
                'y': LaunchConfiguration('y'),
                'z': LaunchConfiguration('z'),
                'yaw': LaunchConfiguration('yaw'),
            }.items(),
        ),
    ])
