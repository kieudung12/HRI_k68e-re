"""AMCL + Nav2 with parameters and RViz configuration bundled inside B7."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory('b7_voice_nav'))
    nav2 = Path(get_package_share_directory('nav2_bringup')) / 'launch/bringup_launch.py'
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=str(share / 'maps/map.yaml')),
        DeclareLaunchArgument('rviz', default_value='true'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(nav2)), launch_arguments={
            'map': LaunchConfiguration('map'), 'use_sim_time': 'true',
            'params_file': str(share / 'config/nav2.yaml'), 'autostart': 'true',
            'use_composition': 'False', 'use_respawn': 'False',
        }.items()),
        Node(package='b7_voice_nav', executable='scan_throttle',
             parameters=[{'use_sim_time': True}], output='screen'),
        Node(package='b7_voice_nav', executable='map_markers',
             parameters=[{'use_sim_time': True, 'map_file': LaunchConfiguration('map')}],
             output='screen'),
        Node(package='rviz2', executable='rviz2',
             arguments=['-d', str(share / 'config/map.rviz')],
             parameters=[{'use_sim_time': True}],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
