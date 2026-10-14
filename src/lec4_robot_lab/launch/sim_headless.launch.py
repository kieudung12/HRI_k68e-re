"""The same simulator without Gazebo's 3D window."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    lab = Path(get_package_share_directory('lec4_robot_lab'))
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='lec4_small_room'),
        DeclareLaunchArgument('model', default_value='lite'),
        DeclareLaunchArgument('rviz', default_value='false'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(lab / 'launch/sim.launch.py')),
            launch_arguments={
                'world': LaunchConfiguration('world'), 'model': LaunchConfiguration('model'),
                'rviz': LaunchConfiguration('rviz'), 'gui': 'false',
            }.items()),
    ])
