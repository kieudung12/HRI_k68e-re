"""Start the upstream UR MoveIt configuration with this robot's URDF/SRDF."""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    own_share = FindPackageShare('ur3_b3')
    upstream = PathJoinSubstitution([
        FindPackageShare('ur_moveit_config'), 'launch', 'ur_moveit.launch.py'
    ])
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(upstream),
        launch_arguments={
            'ur_type': 'ur3e',
            'use_sim_time': 'true',
            'launch_rviz': 'false',
            'description_file': PathJoinSubstitution([
                own_share, 'urdf', 'ur3e_robotiq.urdf.xacro'
            ]),
            'moveit_config_file': PathJoinSubstitution([
                own_share, 'config', 'ur3e_robotiq.srdf.xacro'
            ]),
        }.items(),
    )
    return LaunchDescription([moveit])
