#!/usr/bin/env python3
"""Run Fortress in its own process group and stop its server/GUI on exit."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def existing_servers():
    partition = os.environ.get('IGN_PARTITION', '')
    domain = os.environ.get('ROS_DOMAIN_ID', '0')
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').strip()
            # GUI runs as a parent plus server; headless runs in the CLI process.
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


def session_groups(session_id):
    """Gazebo's GUI/server use separate groups inside the same new session."""
    groups = set()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / 'stat').read_text()
            fields = stat[stat.rfind(')') + 2:].split()
            if fields[0] != 'Z' and int(fields[3]) == session_id:
                groups.add(int(fields[2]))
        except (OSError, ValueError, IndexError):
            continue
    return groups


def main():
    servers = existing_servers()
    if servers:
        print('Gazebo cua bai nay van dang chay (PID: ' + ', '.join(servers) +
              '). Hay dung simulator cu truoc khi mo lai.', file=sys.stderr, flush=True)
        return 2

    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    child = subprocess.Popen(['ign', 'gazebo', *sys.argv[1:], '--force-version', '6'],
                             start_new_session=True)
    try:
        while not stopping and child.poll() is None:
            time.sleep(0.1)
    finally:
        # The CLI forks a server and GUI into separate process groups.
        # Only target groups inside the new session created above.
        for sig, grace in [(signal.SIGINT, 2.0), (signal.SIGTERM, 2.0),
                           (signal.SIGKILL, 0.2)]:
            groups = session_groups(child.pid)
            if not groups:
                break
            for group in groups:
                try:
                    os.killpg(group, sig)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline:
                child.poll()
                if not session_groups(child.pid):
                    return 0 if stopping else (child.returncode or 0)
                time.sleep(0.1)
        child.wait()
    return 0 if stopping else (child.returncode or 0)


if __name__ == '__main__':
    sys.exit(main())
