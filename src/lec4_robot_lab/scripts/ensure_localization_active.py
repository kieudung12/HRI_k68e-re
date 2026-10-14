#!/usr/bin/env python3
"""Wait for lifecycle bringup; recover transitions if DDS loses replies."""

import time
import sys

import rclpy
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState, GetState
from nav2_msgs.srv import ManageLifecycleNodes
from rclpy.node import Node


class LocalizationGate(Node):
    def __init__(self, node_names):
        super().__init__('lec4_lifecycle_gate')
        self.node_names = node_names
        self.recovered = False
        manager = ('lifecycle_manager_navigation' if 'controller_server' in node_names
                   else 'lifecycle_manager_localization')
        self.manager_client = self.create_client(
            ManageLifecycleNodes, f'/{manager}/manage_nodes')
        self.state_clients = {
            name: self.create_client(GetState, f'/{name}/get_state')
            for name in node_names
        }
        self.change_clients = {
            name: self.create_client(ChangeState, f'/{name}/change_state')
            for name in node_names
        }

    def call(self, client, request, timeout=3.0):
        if not client.wait_for_service(timeout_sec=timeout):
            return None
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done() or future.result() is None:
            return None
        return future.result()

    def state(self, name):
        response = self.call(self.state_clients[name], GetState.Request())
        return response.current_state if response else None

    def transition(self, name, transition_id):
        request = ChangeState.Request()
        request.transition.id = transition_id
        response = self.call(self.change_clients[name], request, timeout=5.0)
        return bool(response and response.success)

    def ensure_active(self, name, deadline):
        last_state = None
        while time.monotonic() < deadline:
            current = self.state(name)
            if current is None:
                time.sleep(0.5)
                continue
            state_id = current.id
            if state_id == 3:  # active
                self.get_logger().info(f'/{name} is active.')
                return True
            if current.label != last_state:
                self.get_logger().info(f'/{name} state: {current.label}; waiting for lifecycle bringup.')
                last_state = current.label
            if state_id == 1:
                self.recovered = True
                self.transition(name, Transition.TRANSITION_CONFIGURE)
            elif state_id == 2:
                self.recovered = True
                self.transition(name, Transition.TRANSITION_ACTIVATE)
            time.sleep(0.5)
        self.get_logger().error(f'Timed out waiting for /{name} to become active.')
        return False

    def wait_for_manager(self, timeout=20.0):
        """Give the standard Nav2 lifecycle manager first chance to start nodes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            states = [self.state(name) for name in self.node_names]
            if all(state and state.id == 3 for state in states):
                self.get_logger().info('Lifecycle manager brought up all requested nodes.')
                return
            rclpy.spin_once(self, timeout_sec=0.1)
            time.sleep(0.5)
        self.get_logger().warning('Lifecycle manager did not finish bringup; recovering node transitions.')

    def resync_manager(self):
        """Restore the manager's bonds/state after recovering missed replies."""
        for command in (ManageLifecycleNodes.Request.RESET,
                        ManageLifecycleNodes.Request.STARTUP):
            request = ManageLifecycleNodes.Request()
            request.command = command
            response = self.call(self.manager_client, request, timeout=30.0)
            if not response or not response.success:
                self.get_logger().error('Lifecycle manager recovery failed.')
                return False
        self.get_logger().info('Lifecycle manager and node states are synchronized.')
        return True


def main():
    rclpy.init()
    node_names = sys.argv[1:] or ['map_server', 'amcl']
    node = LocalizationGate(node_names)
    try:
        deadline = time.monotonic() + 90.0
        node.wait_for_manager()
        for name in node_names:
            if not node.ensure_active(name, deadline):
                return 1
        if node.recovered and not node.resync_manager():
            return 1
        node.get_logger().info('Requested lifecycle nodes are active.')
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
