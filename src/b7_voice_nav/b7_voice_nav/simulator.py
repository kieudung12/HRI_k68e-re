"""Own Gazebo processes; start the GUI after simulated sensors are ready."""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def run_gazebo(arguments):
    child = subprocess.Popen(['ign', 'gazebo', *arguments, '--force-version', '6'],
                             start_new_session=True)
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while child.poll() is None and not stopping:
            time.sleep(0.1)
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            if child.poll() is not None:
                break
            try:
                os.killpg(child.pid, sig)
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                continue
            except ProcessLookupError:
                break
    return child.returncode or 0


def server_main():
    # Released automatically on exit; prevents two B7 simulators on this domain.
    lock_path = f"/tmp/b7_gazebo_{os.environ.get('ROS_DOMAIN_ID', '97')}.lock"
    with open(lock_path, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('B7 Gazebo dang chay. Dung phien cu truoc khi mo lai.')
        raise SystemExit(run_gazebo([sys.argv[1], '-r', '-s', '-v', '2']))


def gui_main():
    import rclpy
    from ament_index_python.packages import get_package_share_directory
    from nav_msgs.msg import Odometry
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan

    rclpy.init()
    node = rclpy.create_node('gazebo_gui_wait')
    ready = set()
    node.create_subscription(Odometry, '/odom', lambda _: ready.add('odom'), qos_profile_sensor_data)
    node.create_subscription(LaserScan, '/scan', lambda _: ready.add('scan'), qos_profile_sensor_data)
    node.get_logger().info('Cho robot co /odom va /scan truoc khi mo Gazebo GUI...')
    try:
        while rclpy.ok() and len(ready) < 2:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        return
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    config = Path(get_package_share_directory('b7_voice_nav')) / 'config/gazebo_gui.config'
    raise SystemExit(run_gazebo(['-g', '--gui-config', str(config)]))
