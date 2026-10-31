from glob import glob
from setuptools import setup

package_name = 'b7_voice_nav'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*')),
        ('share/' + package_name + '/maps', glob('maps/*')),
        ('share/' + package_name + '/worlds', glob('worlds/*')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    package_data={package_name: ['prompts/*.txt']},
    install_requires=['setuptools'], zip_safe=True, maintainer='HRI Student',
    maintainer_email='student@example.com', description='Vietnamese voice navigation for TurtleBot 4',
    license='Apache-2.0', entry_points={'console_scripts': [
        'segment_map = b7_voice_nav.segment:main',
        'map_markers = b7_voice_nav.map_markers:main',
        'voice_navigator = b7_voice_nav.navigator:main',
        'speech_recognition = b7_voice_nav.speech:main',
        'scan_throttle = b7_voice_nav.scan_throttle:main',
        'gazebo_server = b7_voice_nav.simulator:server_main',
        'gazebo_gui = b7_voice_nav.simulator:gui_main',
    ]},
)
