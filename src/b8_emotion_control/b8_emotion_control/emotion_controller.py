"""Node ROS nhẹ: nhận nhãn, đọc odom, phát Twist ở 20 Hz."""

import math
import signal
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

from .behavior import Behavior


class EmotionController(Node):
    def __init__(self):
        super().__init__('emotion_controller')
        self.behavior = Behavior()
        # depth=1: chỉ xử lý lệnh mới nhất, không chạy lại lệnh tồn trong hàng đợi.
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 1)
        self.state_pub = self.create_publisher(String, '/emotion_robot_state', 1)
        self.emotion_sub = self.create_subscription(
            String, '/detected_emotion', self.on_emotion, 1)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.create_timer(0.05, self.tick)

    def on_emotion(self, message):
        self.behavior.on_emotion(message.data, time.monotonic())

    def on_odom(self, message):
        q = message.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                         1 - 2 * (q.y * q.y + q.z * q.z))
        self.behavior.on_yaw(yaw, time.monotonic())

    def publish_velocity(self, linear=0.0, angular=0.0):
        msg = Twist()
        msg.linear.x, msg.angular.z = linear, angular
        self.cmd_pub.publish(msg)

    def tick(self):
        self.publish_velocity(*self.behavior.velocity(time.monotonic()))
        self.state_pub.publish(String(data=self.behavior.status))


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = EmotionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if rclpy.ok():
            node.publish_velocity()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
