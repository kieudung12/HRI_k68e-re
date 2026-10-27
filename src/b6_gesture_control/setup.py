from glob import glob
from setuptools import setup

package_name = 'b6_gesture_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='HRI Student',
    maintainer_email='student@example.com',
    description='MediaPipe gestures for TurtleBot 4 behavior control',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'gesture_recognition_node = b6_gesture_control.gesture_recognition_node:main',
        'robot_behavior_node = b6_gesture_control.robot_behavior_node:main',
    ]},
)
