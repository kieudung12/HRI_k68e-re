import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Python trong venv chỉ dùng cho node AI; node điều khiển dùng Python ROS.
    python = os.path.join(os.environ['B8_WS'], '.venv', 'bin', 'python')
    sim = os.path.join(get_package_share_directory('b8_emotion_control'), 'launch', 'sim.launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('sim', default_value='true'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('camera', default_value='0'),
        DeclareLaunchArgument('detector', default_value='opencv'),
        DeclareLaunchArgument('classifier', default_value='hsemotion'),
        DeclareLaunchArgument('stable_frames', default_value='2'),
        DeclareLaunchArgument('confidence', default_value='35.0'),
        DeclareLaunchArgument('display', default_value='true'),
        DeclareLaunchArgument('require_calibration', default_value='true'),
        DeclareLaunchArgument('follow', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(sim), condition=IfCondition(LaunchConfiguration('sim')),
            launch_arguments={'gui': LaunchConfiguration('gui'),
                              'follow': LaunchConfiguration('follow')}.items()),
        Node(package='b8_emotion_control', executable='emotion_controller', output='screen'),
        Node(package='b8_emotion_control', executable='emotion_camera',
             prefix=[python], output='screen', parameters=[{
                 name: ParameterValue(LaunchConfiguration(name), value_type=kind)
                 for name, kind in [('camera', int), ('detector', str), ('classifier', str),
                                    ('stable_frames', int), ('confidence', float), ('display', bool),
                                    ('require_calibration', bool)]
             }]),
    ])
