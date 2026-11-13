from glob import glob
from setuptools import setup

name = 'b8_emotion_control'
setup(
    name=name,
    version='0.1.0',
    packages=[name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + name]),
        ('share/' + name, ['package.xml']),
        ('share/' + name + '/launch', glob('launch/*.launch.py')),
        ('share/' + name + '/worlds', glob('worlds/*.sdf')),
        ('share/' + name + '/config', glob('config/*.config')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='HRI Student',
    maintainer_email='student@example.com',
    description='DeepFace expressions and TurtleBot motion',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'emotion_camera = b8_emotion_control.emotion_camera:main',
        'emotion_controller = b8_emotion_control.emotion_controller:main',
    ]},
)
