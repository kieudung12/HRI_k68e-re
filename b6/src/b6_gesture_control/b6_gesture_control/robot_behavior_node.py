#!/usr/bin/env python3
"""Debounced gesture-to-Twist state machine with a command-loss watchdog."""

from __future__ import annotations

import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String


class RobotBehaviorNode(Node):
    """Select, confirm, pause, resume, and cancel time-segmented robot actions."""

    def __init__(self) -> None:
        super().__init__('robot_behavior_node')
        self.declare_parameter('gesture_topic', '/detected_gesture')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('watchdog_timeout', 0.8)
        self.declare_parameter('control_rate', 20.0)
        gesture_topic = self.get_parameter('gesture_topic').value
        cmd_topic = self.get_parameter('cmd_vel_topic').value
        self.watchdog_timeout = float(self.get_parameter('watchdog_timeout').value)
        rate = max(5.0, float(self.get_parameter('control_rate').value))
        self.publisher = self.create_publisher(Twist, cmd_topic, 10)
        self.subscription = self.create_subscription(String, gesture_topic, self.on_gesture, 10)
        self.state_publisher = self.create_publisher(String, '/robot_behavior_state', 10)
        self.status = 'WAITING | SELECT AN ACTION'
        self.last_heartbeat = time.monotonic()
        self.last_label = 'NONE'
        self.pending_action: str | None = None
        self.active_action: str | None = None
        self.segments: list[tuple[float, float, float]] = []
        self.segment_index = 0
        self.segment_started = 0.0
        self.paused = False
        self.paused_elapsed = 0.0
        self.create_timer(1.0 / rate, self.on_timer)
        self.get_logger().info(
            f'Listening {gesture_topic}; publishing {cmd_topic}. '
            'Pointing Up/Victory/Wave select; Thumbs Up starts/resumes; Palm pauses; Fist cancels.'
        )

    def _publish_velocity(self, linear: float = 0.0, angular: float = 0.0) -> None:
        command = Twist()
        command.linear.x = float(linear)
        command.angular.z = float(angular)
        self.publisher.publish(command)

    def _set_status(self, status: str) -> None:
        self.status = status
        message = String()
        message.data = status
        self.state_publisher.publish(message)

    def _cancel(self) -> None:
        self.active_action = None
        self.segments.clear()
        self.segment_index = 0
        self.segment_started = 0.0
        self.paused = False
        self.paused_elapsed = 0.0
        self.pending_action = None
        self._set_status('WAITING | SELECT AN ACTION')
        self._publish_velocity()
        self.get_logger().info('Closed Fist: canceled action and returned to waiting.')

    def _pause(self, reason: str) -> None:
        if self.active_action:
            if not self.paused:
                self.paused_elapsed = max(0.0, time.monotonic() - self.segment_started)
            self.paused = True
            action_name = self.active_action.replace('_', ' ').upper()
            self._set_status(f'PAUSED | {action_name} | {reason}')
        elif self.pending_action:
            # A selected action has no progress yet; keep it for confirmation.
            self._set_status(f'SELECTED | {self.pending_action.replace("_", " ").upper()}')
        else:
            self._set_status('WAITING | SELECT AN ACTION')
        self._publish_velocity()

    def _resume(self) -> None:
        if not self.active_action or not self.paused:
            return
        # Exclude all time spent paused from the current movement segment.
        self.segment_started = time.monotonic() - self.paused_elapsed
        self.paused = False
        self._set_status(f'RUNNING | {self.active_action.replace("_", " ").upper()}')
        self.get_logger().info(f'Resuming {self.active_action} at segment {self.segment_index}.')

    def on_gesture(self, message: String) -> None:
        now = time.monotonic()
        self.last_heartbeat = now
        label = message.data.strip()
        if label not in {'Wave', 'Pointing_Up', 'Victory', 'Thumb_Up', 'Open_Palm', 'Closed_Fist'}:
            label = 'NONE'

        # React only to gesture edges; repeated heartbeat messages never retrigger an action.
        changed = label != self.last_label
        self.last_label = label
        if not changed:
            return

        if label == 'Open_Palm':
            self._pause('OPEN PALM')
            return
        if label == 'Closed_Fist':
            self._cancel()
            return
        if label == 'NONE':
            # No hand / low confidence is not a stop command. The heartbeat above
            # stays fresh, so any confirmed action continues until it completes
            # or an explicit stop/cancel gesture arrives.
            return

        if label in {'Pointing_Up', 'Victory', 'Wave'}:
            if self.active_action:
                self.get_logger().warning('Action retained; resume with Thumbs Up or cancel with Closed Fist.')
                return
            self.pending_action = {
                'Pointing_Up': 'forward_back',
                'Victory': 'circle',
                'Wave': 'greeting',
            }[label]
            self._set_status(f'SELECTED | {self.pending_action.replace("_", " ").upper()}')
            self.get_logger().info(f'Selected {self.pending_action}; show Thumbs Up to confirm.')
            return

        if label == 'Thumb_Up':
            if self.active_action:
                self._resume()
                return
            if self.pending_action:
                self._start_action(self.pending_action)
                self.pending_action = None
            else:
                self._set_status('WAITING | SELECT AN ACTION')
                self.get_logger().info('Thumbs Up received, but no action is selected.')

    def _start_action(self, action: str) -> None:
        if action == 'forward_back':
            # Four controlled forward/back cycles, with a pause at each reversal.
            self.segments = []
            for _ in range(4):
                self.segments.extend([
                    (1.50, 0.18, 0.0), (0.30, 0.0, 0.0),
                    (1.50, -0.18, 0.0), (0.30, 0.0, 0.0),
                ])
        elif action == 'circle':
            # Low speed and a ~0.38 m radius keep the trajectory compact.
            self.segments = [(12.0, 0.12, 0.32)]
        else:
            # Turn left, then right, then return to the starting heading.
            self.segments = [
                (0.65, 0.0, 0.55), (0.25, 0.0, 0.0),
                (1.30, 0.0, -0.55), (0.25, 0.0, 0.0),
                (0.65, 0.0, 0.55),
            ]
        self.active_action = action
        self.paused = False
        self.paused_elapsed = 0.0
        self._set_status(f'RUNNING | {action.replace("_", " ").upper()}')
        self.segment_index = 0
        self.segment_started = time.monotonic()
        self.get_logger().info(f'Confirmed: executing {action}.')

    def on_timer(self) -> None:
        now = time.monotonic()
        if now - self.last_heartbeat > self.watchdog_timeout:
            self._pause('SIGNAL LOST')
            self.last_label = 'NONE'
            return

        if not self.active_action or self.paused:
            self._publish_velocity()
            self._set_status(self.status)
            return

        duration, linear, angular = self.segments[self.segment_index]
        elapsed = now - self.segment_started
        if elapsed >= duration:
            self.segment_index += 1
            self.segment_started = now
            if self.segment_index >= len(self.segments):
                if self.active_action == 'circle':
                    # Keep circling while the camera is alive; Open Palm or
                    # Closed Fist interrupts it through on_gesture().
                    self.segment_index = 0
                    duration, linear, angular = self.segments[0]
                    self._publish_velocity(linear, angular)
                    self._set_status(self.status)
                    return
                completed = self.active_action
                self.active_action = None
                self.segments.clear()
                self.segment_index = 0
                self.paused_elapsed = 0.0
                self._set_status(f'COMPLETED | {completed.replace("_", " ").upper()}')
                self._publish_velocity()
                self.get_logger().info(f'Completed {completed}.')
                return
            duration, linear, angular = self.segments[self.segment_index]
        self._publish_velocity(linear, angular)
        self._set_status(self.status)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotBehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._publish_velocity()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
