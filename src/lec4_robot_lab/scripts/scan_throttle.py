#!/usr/bin/env python3
"""Forward a lower-rate LaserScan stream for AMCL on slower simulation hosts."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import LaserScan


class ScanThrottle(Node):
    def __init__(self):
        super().__init__('lec4_amcl_scan_throttle')
        self.declare_parameter('input_topic', '/scan')
        self.declare_parameter('output_topic', '/scan_amcl')
        self.declare_parameter('rate', 10.0)
        self.period_ns = int(1e9 / max(1.0, self.get_parameter('rate').value))
        self.last_stamp_ns = -self.period_ns
        # A shallow best-effort queue discards stale scans when the simulator
        # or AMCL cannot keep pace. A deeper queue makes localization lag the
        # simulation clock, which leaves map -> odom unusably old to Nav2.
        latest_scan = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.publisher = self.create_publisher(
            LaserScan, self.get_parameter('output_topic').value, latest_scan)
        self.subscription = self.create_subscription(
            LaserScan, self.get_parameter('input_topic').value,
            self.on_scan, latest_scan)

    def on_scan(self, scan):
        stamp_ns = scan.header.stamp.sec * 1_000_000_000 + scan.header.stamp.nanosec
        if stamp_ns - self.last_stamp_ns >= self.period_ns:
            self.publisher.publish(scan)
            self.last_stamp_ns = stamp_ns


def main():
    rclpy.init()
    node = ScanThrottle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
