"""Keep the latest 10 Hz scans for AMCL; avoid an old sensor backlog."""
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def main():
    rclpy.init()
    node = Node('scan_throttle')
    publisher = node.create_publisher(LaserScan, '/scan_amcl', qos_profile_sensor_data)
    last = [-100_000_000]

    def on_scan(scan):
        stamp = scan.header.stamp.sec * 1_000_000_000 + scan.header.stamp.nanosec
        if stamp < last[0] or stamp - last[0] >= 100_000_000:
            publisher.publish(scan)
            last[0] = stamp

    node.create_subscription(LaserScan, '/scan', on_scan, qos_profile_sensor_data)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
