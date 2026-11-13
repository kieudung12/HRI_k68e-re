"""Sân trống B8; dùng lại phần spawn TurtleBot đã có của lec4."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, Shutdown, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    own = Path(get_package_share_directory('b8_emotion_control'))
    lab = Path(get_package_share_directory('lec4_robot_lab'))
    resources = [str(own / 'worlds')]
    for package in ['turtlebot4_description', 'irobot_create_description']:
        resources.append(str(Path(get_package_share_directory(package)).parent))
    for package in ['turtlebot4_ignition_bringup', 'irobot_create_ignition_bringup']:
        resources.append(str(Path(get_package_share_directory(package)) / 'worlds'))
    environment = {
        'IGN_GAZEBO_RESOURCE_PATH': os.pathsep.join(resources),
        'IGN_GAZEBO_SYSTEM_PLUGIN_PATH': os.pathsep.join([
            os.environ.get('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', ''), os.environ.get('LD_LIBRARY_PATH', '')]),
    }
    session = str(Path(get_package_prefix('lec4_robot_lab')) / 'lib/lec4_robot_lab/gazebo_session.py')
    actions = [
        ExecuteProcess(cmd=[session, str(own / 'worlds/b8_empty.sdf'), '-r', '-v', '2', '-s'],
                       additional_env=environment, output='screen',
                       on_exit=Shutdown(reason='B8 simulator ended')),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='clock_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'], output='screen'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(lab / 'launch/spawn_robot.launch.py')),
            launch_arguments={'world': 'b8_empty', 'model': 'lite'}.items()),
    ]
    if LaunchConfiguration('gui').perform(context) == 'true':
        actions.append(TimerAction(period=3.0, actions=[ExecuteProcess(
            cmd=['ign', 'gazebo', '-g', '--gui-config', str(own / 'config/gazebo_gui.config'),
                 '--force-version', '6'], additional_env=environment, output='screen')]))
        for delay, service, msg_type, request in [
            (8.0, '/gui/follow/offset', 'ignition.msgs.Vector3d', 'x: -1.0 y: -1.0 z: 1.6'),
            (9.0, '/gui/follow', 'ignition.msgs.StringMsg', 'data: "turtlebot4"'),
        ]:
            actions.append(TimerAction(period=delay, actions=[ExecuteProcess(
                cmd=['ign', 'service', '-s', service, '--reqtype', msg_type,
                     '--reptype', 'ignition.msgs.Boolean', '--timeout', '3000', '--req', request],
                condition=IfCondition(LaunchConfiguration('follow')), output='screen')]))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('follow', default_value='true'),
        OpaqueFunction(function=start),
    ])
