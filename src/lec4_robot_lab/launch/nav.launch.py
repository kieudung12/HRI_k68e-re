from pathlib import Path
import math
import runpy
import yaml

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    SetLaunchConfiguration,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def check_runtime(context):
    map_path = Path(LaunchConfiguration('map').perform(context)).expanduser().resolve()
    if not map_path.is_file():
        raise RuntimeError(f'Map YAML khong ton tai: {map_path}')
    try:
        map_data = yaml.safe_load(map_path.read_text())
        if not isinstance(map_data, dict):
            raise ValueError('noi dung map YAML phai la mot object')
        resolution = float(map_data.get('resolution', 0.0))
        image_name = map_data.get('image')
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise RuntimeError(f'Map YAML khong doc duoc: {map_path}: {exc}') from exc
    if not isinstance(image_name, str) or not image_name:
        raise RuntimeError(f'Map YAML thieu ten anh image: {map_path}')
    image_path = Path(image_name).expanduser()
    if not image_path.is_absolute():
        image_path = map_path.parent / image_path
    if not image_path.is_file():
        raise RuntimeError(f'Khong tim thay anh ban do: {image_path}')
    if not math.isfinite(resolution) or resolution <= 0.0:
        raise RuntimeError(f'Map resolution khong hop le: {resolution}')

    prefix = Path(get_package_prefix('lec4_robot_lab'))
    guard = runpy.run_path(str(prefix / 'lib/lec4_robot_lab/runtime_guard.py'))
    sim = guard['gazebo_processes']()
    if not sim:
        raise RuntimeError('Chua thay Gazebo cua lab tren ROS_DOMAIN_ID/IGN_PARTITION hien tai. '
                           'Hay chay sim.launch.py truoc.')

    groups = ['slam', 'localization']
    if LaunchConfiguration('nav2').perform(context) == 'true':
        groups.append('navigation')
    active = guard['matching_processes'](groups)
    if active:
        details = '; '.join(f'{name}: {", ".join(pids)}' for name, pids in active.items())
        raise RuntimeError('Da co stack ROS cua lab dang chay (' + details +
                           '). Dung cac terminal stack do bang Ctrl+C truoc khi mo nav.launch.py.')
    return [SetLaunchConfiguration('map', str(map_path))]


def generate_launch_description():
    navigation = Path(get_package_share_directory('turtlebot4_navigation')) / 'launch'
    lab = Path(get_package_share_directory('lec4_robot_lab'))
    map_file = LaunchConfiguration('map')
    localization_gate = ExecuteProcess(
        cmd=['python3', str(
            Path(get_package_prefix('lec4_robot_lab'))
            / 'lib/lec4_robot_lab/ensure_localization_active.py')],
        output='screen',
    )
    start_navigation = TimerAction(
        period=3.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(navigation / 'nav2.launch.py')),
            launch_arguments={
                'use_sim_time': 'true', 'namespace': '',
                'params_file': str(lab / 'config/nav2.yaml'),
            }.items(),
            condition=IfCondition(LaunchConfiguration('nav2')),
        )],
    )
    start_navigation_gate = TimerAction(
        period=12.0,
        actions=[ExecuteProcess(
            cmd=['python3', str(
                Path(get_package_prefix('lec4_robot_lab'))
                / 'lib/lec4_robot_lab/ensure_localization_active.py'),
                'controller_server', 'smoother_server', 'planner_server',
                'behavior_server', 'bt_navigator', 'waypoint_follower',
                'velocity_smoother',
            ],
            output='screen',
            condition=IfCondition(LaunchConfiguration('nav2')),
        )],
    )
    start_rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(lab / 'launch/view.launch.py')),
        launch_arguments={'enabled': LaunchConfiguration('rviz'), 'frame': 'map'}.items(),
    )
    start_pose_relay = Node(
        package='lec4_robot_lab', executable='initial_pose_relay.py',
        name='initial_pose_relay', output='screen',
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )
    pose_gate = ExecuteProcess(
        cmd=['python3', str(
            Path(get_package_prefix('lec4_robot_lab'))
            / 'lib/lec4_robot_lab/wait_localization_ready.py')],
        output='screen',
        condition=IfCondition(LaunchConfiguration('nav2')),
    )

    def after_localization(event, _context):
        if event.returncode != 0:
            from launch.actions import Shutdown
            return [Shutdown(reason='Localization did not become active; stopping nav launch.')]
        return [start_rviz, start_pose_relay, pose_gate]

    def after_pose_ready(event, _context):
        if event.returncode != 0:
            from launch.actions import LogInfo
            return [LogInfo(msg='Initial pose was not received; Nav2 was not started.')]
        return [start_navigation, start_navigation_gate]

    return LaunchDescription([
        DeclareLaunchArgument(
            'map', default_value=str(lab / 'maps/map.yaml'),
            description='Map YAML saved from the SLAM run'),
        DeclareLaunchArgument('nav2', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        OpaqueFunction(function=check_runtime),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(navigation / 'localization.launch.py')),
            launch_arguments={
                'use_sim_time': 'true', 'map': map_file, 'namespace': '',
                'params': str(lab / 'config/localization.yaml'),
            }.items(),
        ),
        Node(
            package='lec4_robot_lab', executable='scan_throttle.py',
            name='amcl_scan_throttle', output='screen',
            # The previous 1.5 Hz throttle let AMCL's map -> odom transform
            # become stale during longer goals. 10 Hz keeps localization
            # current while still reducing Gazebo's ~62 Hz scan stream.
            parameters=[{'use_sim_time': True, 'rate': 10.0}],
        ),
        Node(
            package='lec4_robot_lab', executable='amcl_tf_watchdog.py',
            name='amcl_tf_watchdog', output='screen',
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(LaunchConfiguration('nav2')),
        ),
        RegisterEventHandler(OnProcessExit(
            target_action=localization_gate, on_exit=after_localization)),
        RegisterEventHandler(OnProcessExit(
            target_action=pose_gate, on_exit=after_pose_ready)),
        localization_gate,
    ])
