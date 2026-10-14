from pathlib import Path
import runpy

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def check_runtime(_context):
    prefix = Path(get_package_prefix('lec4_robot_lab'))
    guard = runpy.run_path(str(prefix / 'lib/lec4_robot_lab/runtime_guard.py'))
    if not guard['gazebo_processes']():
        raise RuntimeError('Chua thay Gazebo cua lab tren ROS_DOMAIN_ID/IGN_PARTITION hien tai.')
    active = guard['matching_processes'](['slam', 'localization', 'navigation'])
    if active:
        details = '; '.join(f'{name}: {", ".join(pids)}' for name, pids in active.items())
        raise RuntimeError('Da co stack SLAM/localization/Nav2 dang chay (' + details +
                           '). Dung stack cu bang Ctrl+C truoc khi mo mapping.')
    return []


def generate_launch_description():
    navigation = Path(get_package_share_directory('turtlebot4_navigation'))
    lab = Path(get_package_share_directory('lec4_robot_lab'))
    slam = navigation / 'launch/slam.launch.py'

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        OpaqueFunction(function=check_runtime),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(slam)),
            launch_arguments={
                'use_sim_time': 'true',
                'sync': 'false',
                'namespace': '',
                'params': str(lab / 'config/slam_mapping.yaml'),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(lab / 'launch/view.launch.py')),
            launch_arguments={'enabled': LaunchConfiguration('rviz'), 'frame': 'map'}.items(),
        ),
    ])
