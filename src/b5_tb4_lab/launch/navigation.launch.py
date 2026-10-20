"""Load the B5 map and start lec4 AMCL, Nav2, and RViz configuration."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    lec4_share = get_package_share_directory('lec4_robot_lab')
    nav_launch = lec4_share + '/launch/nav.launch.py'
    b5_share = get_package_share_directory('b5_tb4_lab')
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=b5_share + '/maps/map.yaml'),
        DeclareLaunchArgument('nav2', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_launch),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'nav2': LaunchConfiguration('nav2'),
                'rviz': LaunchConfiguration('rviz'),
            }.items(),
        ),
    ])
