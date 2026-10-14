#!/usr/bin/env python3
"""Wait until AMCL has accepted a pose and map -> odom TF is current."""

import time
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from rosgraph_msgs.msg import Clock
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener


def main():
    rclpy.init()
    node = rclpy.create_node('lec4_wait_localization_ready')
    node.set_parameters([Parameter('use_sim_time', value=True)])
    buffer = Buffer(node=node)
    listener = TransformListener(buffer, node)
    received_pose = [False]
    sim_time_ns = [0]
    qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )
    node.create_subscription(
        PoseWithCovarianceStamped, '/amcl_pose',
        lambda _msg: received_pose.__setitem__(0, True), qos)
    node.create_subscription(
        Clock, '/clock', lambda msg: sim_time_ns.__setitem__(
            0, msg.clock.sec * 1_000_000_000 + msg.clock.nanosec), 10)
    nomotion_update = node.create_client(Empty, '/request_nomotion_update')
    update_future = None
    last_update_request = 0.0
    freshness_ns = 2_000_000_000
    node.get_logger().info(
        'Waiting for RViz 2D Pose Estimate and fresh AMCL map->odom TF; Nav2 will not start on stale TF.')
    ready = False
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if not received_pose[0] or sim_time_ns[0] == 0:
                continue

            current_tf_ns = 0
            try:
                transform = buffer.lookup_transform('map', 'odom', Time())
                current_tf_ns = (
                    transform.header.stamp.sec * 1_000_000_000
                    + transform.header.stamp.nanosec
                )
            except Exception:
                pass

            # AMCL may keep an old transform while the robot is stationary.
            # Ask it to process the latest scan without requiring movement.
            now_wall = time.monotonic()
            if (current_tf_ns == 0 or
                    abs(sim_time_ns[0] - current_tf_ns) > freshness_ns):
                if (now_wall - last_update_request > 1.0 and
                        nomotion_update.service_is_ready()):
                    update_future = nomotion_update.call_async(Empty.Request())
                    last_update_request = now_wall
                continue

            if buffer.can_transform('map', 'base_link', Time()):
                node.get_logger().info(
                    f'AMCL pose and fresh map->odom TF are ready '
                    f'(clock={sim_time_ns[0] / 1e9:.3f}s, tf={current_tf_ns / 1e9:.3f}s).')
                ready = True
                break
    except KeyboardInterrupt:
        pass
    finally:
        listener.unregister()
        node.destroy_node()
        rclpy.shutdown()
    return 0 if ready else 1


if __name__ == '__main__':
    raise SystemExit(main())
