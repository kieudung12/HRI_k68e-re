"""Gazebo world with a UR3e, Robotiq gripper and physical colored cubes."""

from launch import LaunchDescription
import os

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('ur3_b3')
    # Gazebo converts package:// mesh URIs to model://. Include the parent of
    # the installed Robotiq package so those models resolve in both renderers.
    robotiq_models = os.path.dirname(get_package_share_directory('robotiq_description'))
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('ur_simulation_gz'), 'launch', 'ur_sim_control.launch.py'
        ])),
        launch_arguments={
            'ur_type': 'ur3e',
            'description_package': 'ur3_b3',
            'description_file': 'ur3e_robotiq.urdf.xacro',
            'runtime_config_package': 'ur3_b3',
            'controllers_file': 'controllers.yaml',
            'initial_joint_controller': 'joint_trajectory_controller',
            'launch_rviz': 'false',
            'gazebo_gui': LaunchConfiguration('gui'),
            'world_file': PathJoinSubstitution([share, 'worlds', 'table.sdf']),
        }.items(),
    )
    gripper_controller = Node(
        package='controller_manager', executable='spawner', output='screen',
        arguments=['gripper_controller', '-c', '/controller_manager'],
    )
    camera_bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge', output='screen',
        arguments=[
            '/camera@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        ],
    )
    perception = Node(
        package='ur3_b3', executable='perception', output='screen',
        parameters=[{'use_sim_time': True}],
    )
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false'),
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', [
            robotiq_models, ':', EnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', default_value='')
        ]),
        simulation,
        gripper_controller,
        camera_bridge,
        perception,
    ])
