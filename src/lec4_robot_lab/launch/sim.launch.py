"""One Gazebo session, official TurtleBot spawn, and optional RViz."""
import os
from pathlib import Path
import runpy

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, Shutdown, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_sim(context):
    lab = Path(get_package_share_directory('lec4_robot_lab'))
    tb4 = Path(get_package_share_directory('turtlebot4_ignition_bringup'))
    create = Path(get_package_share_directory('irobot_create_ignition_bringup'))
    world = LaunchConfiguration('world').perform(context)
    model = LaunchConfiguration('model').perform(context)
    world_file = next((p / 'worlds' / (world + '.sdf') for p in [lab, tb4, create]
                       if (p / 'worlds' / (world + '.sdf')).is_file()), None)
    if world_file is None:
        raise RuntimeError('Khong tim thay world: ' + world)
    resources = [str(p / 'worlds') for p in [lab, tb4, create]]
    resources += [str(Path(get_package_share_directory(p)).parent)
                  for p in ['turtlebot4_description', 'irobot_create_description']]
    gui_plugins = [str(Path(get_package_share_directory(p)) / 'lib')
                   for p in ['turtlebot4_ignition_gui_plugins', 'irobot_create_ignition_plugins']]
    environment = {
        'IGN_GAZEBO_RESOURCE_PATH': os.pathsep.join(resources),
        'IGN_GUI_PLUGIN_PATH': os.pathsep.join(gui_plugins),
        'IGN_GAZEBO_SYSTEM_PLUGIN_PATH': os.pathsep.join([
            os.environ.get('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', ''),
            os.environ.get('LD_LIBRARY_PATH', '')]),
    }
    # Start the physics server independently. Starting server and GUI in one
    # Fortress CLI process intermittently stalled before controller creation.
    args = [str(world_file), '-r', '-v', '2', '-s']
    gui_actions = []
    if LaunchConfiguration('gui').perform(context) == 'true':
        gui_actions = [TimerAction(period=3.0, actions=[ExecuteProcess(
            cmd=['ign', 'gazebo', '-g', '--gui-config',
                 str(lab / 'config/gazebo_gui.config'), '--force-version', '6'],
            additional_env=environment, output='screen')])]
    executable = Path(get_package_prefix('lec4_robot_lab')) / 'lib/lec4_robot_lab/gazebo_session.py'
    servers = runpy.run_path(str(executable))['existing_servers']()
    if servers:
        raise RuntimeError('Gazebo cua bai nay van dang chay (PID: ' + ', '.join(servers) +
                           '). Dung simulator cu truoc khi mo lai.')
    guard = runpy.run_path(str(Path(get_package_prefix('lec4_robot_lab')) /
                               'lib/lec4_robot_lab/runtime_guard.py'))
    stacks = guard['matching_processes'](['slam', 'localization', 'navigation'])
    if stacks:
        details = '; '.join(f'{name}: {", ".join(pids)}' for name, pids in stacks.items())
        raise RuntimeError('Van con stack SLAM/localization/Nav2 (' + details +
                           '). Dung cac terminal stack nay truoc khi khoi dong lai Gazebo; '
                           'khong de TF buffer cua phien cu song qua lan reset /clock.')
    return [
        ExecuteProcess(cmd=[str(executable), *args], additional_env=environment,
                       output='screen', sigterm_timeout='8', sigkill_timeout='10',
                       on_exit=Shutdown(reason='Gazebo session ended')),
        *gui_actions,
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='clock_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'], output='screen'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(lab / 'launch/spawn_robot.launch.py')),
            launch_arguments={
                'world': world, 'model': model, 'namespace': '',
            }.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(lab / 'launch/view.launch.py')),
            launch_arguments={'enabled': LaunchConfiguration('rviz'), 'frame': 'odom'}.items()),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='lec4_small_room'),
        DeclareLaunchArgument('model', default_value='lite', choices=['standard', 'lite']),
        DeclareLaunchArgument('rviz', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false']),
        OpaqueFunction(function=start_sim),
    ])
