#!/usr/bin/env python3
"""Forward RViz initial poses with a safe TF timestamp margin."""

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


class InitialPoseRelay(Node):
    def __init__(self):
        super().__init__('lec4_initial_pose_relay')
        self.publisher = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', 10)
        self.subscription = self.create_subscription(
            PoseWithCovarianceStamped, '/initialpose_rviz', self.forward_pose, 10)
        self.latest_odom_stamp = None
        self.odom_subscription = self.create_subscription(
            Odometry, '/odom', self.capture_odometry, 10)

    def capture_odometry(self, odometry):
        self.latest_odom_stamp = odometry.header.stamp

    def forward_pose(self, pose):
        # AMCL transforms the supplied pose using odom -> base_link at this
        # timestamp. Use a recent timestamp known to exist in odometry/TF,
        # instead of estimating a fixed offset from /clock. The latter can be
        # wrong when simulation and bridge callbacks are briefly out of sync.
        if self.latest_odom_stamp is None:
            self.get_logger().warning(
                'No /odom sample yet; wait for odometry and set 2D Pose Estimate again.')
            return
        stamp_ns = (
            self.latest_odom_stamp.sec * 1_000_000_000
            + self.latest_odom_stamp.nanosec
        )
        # Runtime showed AMCL's TF listener lagging /odom by 65 ms during
        # startup. Keep 200 ms of history while the robot is stationary.
        margin_ns = 200_000_000
        if stamp_ns <= margin_ns:
            self.get_logger().warning(
                'Latest /odom time is too close to zero; set 2D Pose Estimate again shortly.')
            return
        stamp_ns -= margin_ns
        pose.header.stamp.sec, pose.header.stamp.nanosec = divmod(
            stamp_ns, 1_000_000_000)
        self.publisher.publish(pose)
        self.get_logger().info(
            'Forwarded RViz initial pose using /odom time minus 0.20 s.')


def main():
    rclpy.init()
    node = InitialPoseRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
