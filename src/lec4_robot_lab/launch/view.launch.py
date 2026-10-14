"""RViz only, using the description and TF already published by the simulator."""
from pathlib import Path
import os
from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def view(context):
    if LaunchConfiguration('enabled').perform(context) != 'true':
        return []
    frame = LaunchConfiguration('frame').perform(context)
    config_dir = Path(get_package_share_directory('lec4_robot_lab')) / 'config'
    config = config_dir / (frame + '.rviz')
    duplicates = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            command = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
        except (OSError, UnicodeError):
            continue
        if 'rviz2' in command and str(config_dir) in command:
            duplicates.append(entry.name)
    if duplicates:
        raise RuntimeError(
            'RViz cua lec4_robot_lab da chay (PID: ' + ', '.join(duplicates) +
            '). Dung RViz cu bang Ctrl+C trong terminal da mo no truoc khi mo lai.'
        )
    environment = {}
    if frame == 'map':
        # Keep the Nav2 plugin mapped until ROS callbacks have been destroyed.
        plugin = Path(get_package_prefix('nav2_rviz_plugins')) / 'lib/libnav2_rviz_plugins.so'
        environment['LD_PRELOAD'] = str(plugin)
    return [Node(package='rviz2', executable='rviz2', name='rviz2', output='screen',
                 arguments=['-d', str(config)], parameters=[{'use_sim_time': True}],
                 additional_env=environment)]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('enabled', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('frame', default_value='map', choices=['odom', 'map']),
        OpaqueFunction(function=view),
    ])
