#!/usr/bin/env python3
"""Small /proc checks shared by the lab launch files."""
from pathlib import Path


PROCESS_MARKERS = {
    'slam': ('slam_toolbox/',),
    'localization': (
        'nav2_amcl/amcl', 'nav2_map_server/map_server',
        '__node:=lifecycle_manager_localization',
    ),
    'navigation': (
        'nav2_controller/controller_server',
        'nav2_planner/planner_server',
        'nav2_bt_navigator/bt_navigator',
        '__node:=lifecycle_manager_navigation',
    ),
    'teleop': ('drive_wasd.py', 'teleop_twist_keyboard', 'teleop_keyboard'),
}


def matching_processes(groups):
    """Return {category: [pid, ...]} for matching live ROS processes."""
    markers = {marker: category for category in groups
               for marker in PROCESS_MARKERS[category]}
    result = {category: [] for category in groups}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / 'cmdline').read_bytes()
            if not raw:
                continue
            command = raw.replace(b'\0', b' ').decode(errors='replace')
        except OSError:
            continue
        for marker, category in markers.items():
            if marker in command:
                result[category].append(entry.name)
                break
    return {category: pids for category, pids in result.items() if pids}


def gazebo_processes():
    """Return PIDs belonging to the selected lab's Gazebo partition/domain."""
    import os

    partition = os.environ.get('IGN_PARTITION', '')
    domain = os.environ.get('ROS_DOMAIN_ID', '0')
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').strip()
            if not command.startswith(b'ign gazebo ') or command.startswith(b'ign gazebo gui'):
                continue
            env = dict(item.split(b'=', 1) for item in
                       (entry / 'environ').read_bytes().split(b'\0') if b'=' in item)
            if (env.get(b'IGN_PARTITION', b'').decode() == partition and
                    env.get(b'ROS_DOMAIN_ID', b'0').decode() == domain):
                found.append(entry.name)
        except (OSError, UnicodeError):
            continue
    return found
