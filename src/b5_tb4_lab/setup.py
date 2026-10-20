from glob import glob
from setuptools import setup

package_name = 'b5_tb4_lab'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/maps', glob('maps/*')),
        ('share/' + package_name + '/worlds', glob('worlds/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='HRI Student',
    maintainer_email='student@example.com',
    description='TurtleBot 4 navigation and YOLO lab nodes',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'autonomous_yolo = b5_tb4_lab.autonomous_yolo:main',
        ],
    },
)
