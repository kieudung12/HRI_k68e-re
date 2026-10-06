from setuptools import setup

package_name = 'ur3_b3'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/sim.launch.py', 'launch/moveit.launch.py'
        ]),
        ('share/' + package_name + '/worlds', ['worlds/table.sdf']),
        ('share/' + package_name + '/urdf', ['urdf/ur3e_robotiq.urdf.xacro']),
        ('share/' + package_name + '/config', [
            'config/controllers.yaml', 'config/ur3e_robotiq.srdf.xacro'
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='HRI student',
    maintainer_email='student@example.com',
    description='UR3e tabletop sorting exercise',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'perception = ur3_b3.perception:main',
            'task = ur3_b3.task:main',
        ],
    },
)
