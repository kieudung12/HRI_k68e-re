#!/usr/bin/env python3
"""Keep AMCL's map -> odom transform current during long stationary periods."""

import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node
from rclpy.time import Time
from rosgraph_msgs.msg import Clock
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener


class AmclTfWatchdog(Node):
    def __init__(self):
        super().__init__('lec4_amcl_tf_watchdog')
        self.clock_ns = 0
        self.have_pose = False
        self.last_request = 0.0
        self.last_fresh = False
        self.request_future = None
        self.tf_buffer = Buffer(node=self)
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_subscription(Clock, '/clock', self.on_clock, 10)
        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self.on_pose, 10)
        self.update_client = self.create_client(
            Empty, '/request_nomotion_update')
        self.create_timer(0.2, self.check_transform)

    def on_clock(self, message):
        self.clock_ns = message.clock.sec * 1_000_000_000 + message.clock.nanosec

    def on_pose(self, _message):
        self.have_pose = True

    def check_transform(self):
        if not self.have_pose or self.clock_ns == 0:
            return
        tf_stamp_ns = 0
        try:
            transform = self.tf_buffer.lookup_transform('map', 'odom', Time())
            tf_stamp_ns = (
                transform.header.stamp.sec * 1_000_000_000
                + transform.header.stamp.nanosec
            )
        except Exception:
            pass

        age_ns = self.clock_ns - tf_stamp_ns
        fresh = tf_stamp_ns > 0 and age_ns <= 500_000_000
        if fresh:
            if not self.last_fresh:
                self.get_logger().info('AMCL map->odom transform is fresh again.')
            self.last_fresh = True
            return

        self.last_fresh = False
        now = time.monotonic()
        if (now - self.last_request < 0.5 or
                self.request_future is not None and not self.request_future.done()):
            return
        if not self.update_client.service_is_ready():
            return
        self.request_future = self.update_client.call_async(Empty.Request())
        self.last_request = now
        self.get_logger().warning(
            f'AMCL map->odom is stale by {age_ns / 1e9:.2f}s; '
            'requesting a no-motion update.')


def main():
    rclpy.init()
    node = AmclTfWatchdog()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.tf_listener.unregister()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
