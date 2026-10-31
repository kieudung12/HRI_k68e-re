import math
import os

import rclpy
from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
from .common import load_regions, parse_command


class VoiceNavigator(Node):
    def __init__(self):
        super().__init__('voice_navigator')
        default = os.path.join(get_package_share_directory('b7_voice_nav'), 'config/regions.yaml')
        self.declare_parameter('regions_file', default)
        self.regions = load_regions(self.get_parameter('regions_file').value)
        self.client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.create_subscription(String, 'voice_command', self.on_command, 10)
        self.queue = []
        self.busy = False
        self.get_logger().info('Chờ lệnh tại /voice_command')

    def on_command(self, msg):
        if self.busy:
            self.get_logger().warning('Đang điều hướng; bỏ qua lệnh mới')
            return
        try:
            route = parse_command(msg.data, self.regions)
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return
        if not self.client.server_is_ready():
            self.get_logger().error('Nav2 chưa sẵn sàng; kiểm tra localization và action server')
            return
        self.queue = route
        self.busy = True
        self.send_next()

    def send_next(self):
        if not self.queue:
            self.busy = False
            self.get_logger().info('Đã hoàn thành hành trình')
            return
        region = self.queue.pop(0)
        g = region['goal']
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(g['x'])
        goal.pose.pose.position.y = float(g['y'])
        goal.pose.pose.orientation.z = math.sin(float(g['yaw']) / 2)
        goal.pose.pose.orientation.w = math.cos(float(g['yaw']) / 2)
        self.get_logger().info(f"Đang gửi đích {region['name']}")
        self.client.send_goal_async(goal).add_done_callback(self.goal_response)

    def goal_response(self, future):
        try:
            handle = future.result()
            if not handle.accepted:
                raise RuntimeError('Nav2 từ chối goal')
            handle.get_result_async().add_done_callback(self.result_callback)
        except Exception as exc:
            self.abort(str(exc))

    def result_callback(self, future):
        try:
            status = future.result().status
            if status != GoalStatus.STATUS_SUCCEEDED:
                raise RuntimeError(f'Nav2 không hoàn thành goal (status={status})')
            self.send_next()
        except Exception as exc:
            self.abort(str(exc))

    def abort(self, reason):
        self.queue = []
        self.busy = False
        self.get_logger().error(f'Dừng hành trình: {reason}')


def main():
    rclpy.init()
    node = VoiceNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
