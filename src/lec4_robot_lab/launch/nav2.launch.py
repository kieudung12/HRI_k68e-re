"""Start one Nav2 stack after localization has produced map->odom."""
import runpy
from pathlib import Path

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def reject_duplicate_nav2(context):
    prefix = Path(get_package_prefix('lec4_robot_lab'))
    guard = runpy.run_path(str(prefix / 'lib/lec4_robot_lab/runtime_guard.py'))
    if not guard['gazebo_processes']():
        raise RuntimeError('Chua thay Gazebo cua lab tren ROS_DOMAIN_ID/IGN_PARTITION hien tai.')
    active = guard['matching_processes'](['navigation'])
    if active:
        existing = ', '.join(pid for pids in active.values() for pid in pids)
        raise RuntimeError(
            'Nav2 da chay (PID: ' + existing +
            '). Dung stack cu bang Ctrl+C trong terminal cua no truoc khi mo lai.'
        )
    localization = guard['matching_processes'](['localization'])
    if len(localization.get('localization', [])) < 2:
        raise RuntimeError('Chua co ca map_server va AMCL. Neu muon chay tach, hay mo '
                           'nav.launch.py nav2:=false truoc; khong mo nav2.launch.py don le.')
    if guard['matching_processes'](['teleop']):
        raise RuntimeError('Teleop van dang chay. Thoat teleop truoc khi khoi dong Nav2.')
    return []


def generate_launch_description():
    navigation = Path(get_package_share_directory('turtlebot4_navigation')) / 'launch'
    return LaunchDescription([
        OpaqueFunction(function=reject_duplicate_nav2),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(navigation / 'nav2.launch.py')),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': '',
            }.items(),
        ),
    ])
