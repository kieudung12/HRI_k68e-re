"""Reuse the TurtleBot 4 simulation world configured in lec4."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    lec4_launch = get_package_share_directory('lec4_robot_lab') + '/launch/sim.launch.py'
    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='lec4_small_room', choices=['lec4_small_room']),
        DeclareLaunchArgument('model', default_value='lite'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lec4_launch),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'model': LaunchConfiguration('model'),
                'gui': LaunchConfiguration('gui'),
                'rviz': LaunchConfiguration('rviz'),
            }.items(),
        ),
        # Replace the southeast box landmark with a camera-visible chair
        # target. The chair occupies roughly the same map area, so this
        # does not change the route layout saved in the map.
        TimerAction(period=10.0, actions=[ExecuteProcess(
            cmd=[
                'ign', 'service', '-s',
                '/world/lec4_small_room/remove',
                '--reqtype', 'ignition.msgs.Entity',
                '--reptype', 'ignition.msgs.Boolean',
                '--timeout', '3000', '-r',
                'name: "landmark_southeast", type: MODEL',
            ],
            output='screen',
        )]),
        TimerAction(period=13.0, actions=[ExecuteProcess(
            cmd=[
                'ros2', 'run', 'ros_gz_sim', 'create',
                '-world', LaunchConfiguration('world'),
                '-file', get_package_share_directory('b5_tb4_lab')
                + '/worlds/chair_target.sdf',
                '-name', 'chair_target',
                '-x', '3.1', '-y', '-3.1', '-z', '0.0',
            ],
            output='screen',
        )]),
    ])
