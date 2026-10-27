"""Offline transition tests: no ROS graph, camera, or robot commands are used."""

import importlib.util
from collections import deque
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class String:
    def __init__(self, data=''):
        self.data = data


class Twist:
    def __init__(self):
        self.linear = SimpleNamespace(x=0.0, y=0.0, z=0.0)
        self.angular = SimpleNamespace(x=0.0, y=0.0, z=0.0)


class FakeNode:
    def __init__(self, name):
        self.parameters = {}
        self.publishers = {}
        self.logger = Mock()

    def declare_parameter(self, name, value):
        self.parameters[name] = value

    def get_parameter(self, name):
        return SimpleNamespace(value=self.parameters[name])

    def create_publisher(self, message_type, topic, depth):
        publisher = Mock()
        self.publishers[topic] = publisher
        return publisher

    def create_subscription(self, *args):
        return Mock()

    def create_timer(self, *args):
        return Mock()

    def get_logger(self):
        return self.logger


def load_node(filename):
    """Import the real implementation against minimal ROS/message adapters."""
    modules = {}
    for name in ('rclpy', 'rclpy.node', 'geometry_msgs', 'geometry_msgs.msg',
                 'std_msgs', 'std_msgs.msg', 'cv2', 'mediapipe'):
        modules[name] = ModuleType(name)
    modules['rclpy.node'].Node = FakeNode
    modules['geometry_msgs.msg'].Twist = Twist
    modules['std_msgs.msg'].String = String
    path = Path(__file__).resolve().parents[1] / 'b6_gesture_control' / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', modules):
        spec.loader.exec_module(module)
    return module


behavior = load_node('robot_behavior_node.py')
recognition = load_node('gesture_recognition_node.py')


class BehaviorTransitions(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        clock = patch.object(behavior.time, 'monotonic', lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.node = behavior.RobotBehaviorNode()

    def gesture(self, label):
        self.node.on_gesture(String(label))

    def tick(self, seconds, heartbeat=True):
        self.now += seconds
        if heartbeat:
            self.node.last_heartbeat = self.now
        self.node.on_timer()

    def velocity(self):
        msg = self.node.publisher.publish.call_args.args[0]
        return msg.linear.x, msg.angular.z

    def start(self, label):
        self.gesture(label)
        self.gesture('Thumb_Up')

    def test_pause_and_resume_remaining_segment_for_all_actions(self):
        for label in ('Pointing_Up', 'Victory', 'Wave'):
            with self.subTest(label=label):
                self.node = behavior.RobotBehaviorNode()
                self.start(label)
                original = list(self.node.segments)
                duration = original[0][0]
                self.tick(0.25)
                self.gesture('Open_Palm')
                self.assertTrue(self.node.paused)
                self.assertEqual(self.velocity(), (0.0, 0.0))
                self.assertAlmostEqual(self.node.paused_elapsed, 0.25)
                # Repeated palm events and a long pause must not consume progress.
                self.tick(40)
                self.gesture('NONE')
                self.gesture('Open_Palm')
                self.assertAlmostEqual(self.node.paused_elapsed, 0.25)
                self.assertEqual(self.node.segments, original)
                self.assertEqual(self.node.segment_index, 0)
                self.assertEqual(self.velocity(), (0.0, 0.0))
                self.gesture('Thumb_Up')
                self.assertFalse(self.node.paused)
                self.tick(duration - 0.25 - 0.01)
                self.assertEqual(self.node.segment_index, 0)
                self.assertEqual(self.velocity(), original[0][1:])
                self.tick(0.02)
                self.assertEqual(self.node.segment_index, 0 if label == 'Victory' else 1)

    def test_selection_and_thumb_up_heartbeat_do_not_restart_retained_action(self):
        self.start('Wave')
        self.tick(0.3)
        self.gesture('Open_Palm')
        self.gesture('Victory')
        self.assertEqual(self.node.active_action, 'greeting')
        self.assertTrue(self.node.paused)
        self.gesture('Thumb_Up')
        started = self.node.segment_started
        self.tick(0.1)
        self.gesture('Thumb_Up')
        self.assertEqual(self.node.segment_started, started)

    def test_second_pause_keeps_progress_in_later_segment(self):
        self.start('Wave')
        self.tick(0.66)
        self.tick(0.26)
        self.assertEqual(self.node.segment_index, 2)
        self.tick(0.2)
        self.gesture('Open_Palm')
        elapsed = self.node.paused_elapsed
        self.tick(10)
        self.gesture('Thumb_Up')
        self.tick(0.1)
        self.gesture('Open_Palm')
        self.assertEqual(self.node.segment_index, 2)
        self.assertAlmostEqual(self.node.paused_elapsed, elapsed + 0.1)

    def test_fist_cancels_running_paused_and_pending_actions(self):
        for phase in ('pending', 'running', 'paused'):
            with self.subTest(phase=phase):
                self.node = behavior.RobotBehaviorNode()
                self.gesture('Wave')
                if phase != 'pending':
                    self.gesture('Thumb_Up')
                if phase == 'paused':
                    self.tick(0.2)
                    self.gesture('Open_Palm')
                self.gesture('Closed_Fist')
                self.assertIsNone(self.node.active_action)
                self.assertIsNone(self.node.pending_action)
                self.assertEqual(self.node.segments, [])
                self.assertFalse(self.node.paused)
                self.assertEqual(self.node.status, 'WAITING | SELECT AN ACTION')
                self.assertEqual(self.velocity(), (0.0, 0.0))
                self.gesture('Thumb_Up')
                self.tick(0.1)
                self.assertEqual(self.velocity(), (0.0, 0.0))

    def test_open_palm_preserves_any_pending_selection(self):
        for label, action in (('Wave', 'greeting'), ('Victory', 'circle'),
                              ('Pointing_Up', 'forward_back')):
            with self.subTest(label=label):
                self.node = behavior.RobotBehaviorNode()
                self.gesture(label)
                self.gesture('Open_Palm')
                self.assertEqual(self.node.pending_action, action)
                self.assertEqual(self.velocity(), (0.0, 0.0))
                self.gesture('Thumb_Up')
                self.assertEqual(self.node.active_action, action)

    def test_watchdog_pauses_without_auto_resume_or_losing_progress(self):
        self.start('Pointing_Up')
        self.tick(0.2)
        self.tick(0.81, heartbeat=False)
        elapsed = self.node.paused_elapsed
        self.assertTrue(self.node.paused)
        self.assertIn('SIGNAL LOST', self.node.status)
        self.assertEqual(self.velocity(), (0.0, 0.0))
        self.tick(5, heartbeat=False)
        self.assertEqual(self.node.paused_elapsed, elapsed)
        self.gesture('NONE')
        self.tick(0.1)
        self.assertTrue(self.node.paused)
        self.gesture('Thumb_Up')
        self.assertFalse(self.node.paused)
        self.assertAlmostEqual(self.now - self.node.segment_started, elapsed)

    def test_completed_greeting_does_not_replay_on_thumb_up(self):
        self.start('Wave')
        for duration, _, _ in list(self.node.segments):
            self.tick(duration + 0.01)
        self.assertIsNone(self.node.active_action)
        self.assertEqual(self.node.status, 'COMPLETED | GREETING')
        self.gesture('NONE')
        self.gesture('Thumb_Up')
        self.tick(0.1)
        self.assertIsNone(self.node.active_action)
        self.assertEqual(self.velocity(), (0.0, 0.0))

    def test_paused_finite_actions_complete_without_repeating_previous_segments(self):
        for label in ('Wave', 'Pointing_Up'):
            with self.subTest(label=label):
                self.node = behavior.RobotBehaviorNode()
                self.start(label)
                segments = list(self.node.segments)
                for duration, _, _ in segments[:2]:
                    self.tick(duration + 0.01)
                self.assertEqual(self.node.segment_index, 2)
                self.tick(segments[2][0] * 0.3)
                self.gesture('Open_Palm')
                elapsed = self.node.paused_elapsed
                self.tick(100)
                self.gesture('Thumb_Up')
                self.tick(segments[2][0] - elapsed + 0.01)
                self.assertEqual(self.node.segment_index, 3)
                for index in range(3, len(segments)):
                    self.assertEqual(self.node.segment_index, index)
                    self.tick(segments[index][0] + 0.01)
                self.assertIsNone(self.node.active_action)
                self.assertTrue(self.node.status.startswith('COMPLETED |'))
                self.assertEqual(self.velocity(), (0.0, 0.0))


class RecognitionPriority(unittest.TestCase):
    def test_end_of_wave_remains_selected_until_confirmation(self):
        node = recognition.GestureRecognitionNode.__new__(recognition.GestureRecognitionNode)
        node.min_confidence = 0.6
        node.robot_status = 'SELECTED | GREETING'
        node.positions = deque()
        node.wave_latched = True
        node.wave_hold_until = 1.0
        node._wave_status = Mock(return_value=(False, False))
        self.assertEqual(node._resolve_candidate('Open_Palm', 0.9, [], 100), ('Wave', False))
        self.assertEqual(node._resolve_candidate('Thumb_Up', 0.9, [], 100), ('Thumb_Up', False))

    def test_wave_latch_cannot_hide_pause_during_running_or_paused_action(self):
        for status in ('RUNNING | GREETING', 'RUNNING | CIRCLE',
                       'PAUSED | FORWARD BACK | OPEN PALM'):
            with self.subTest(status=status):
                node = recognition.GestureRecognitionNode.__new__(recognition.GestureRecognitionNode)
                node.min_confidence = 0.6
                node.robot_status = status
                node.positions = deque()
                node.wave_latched = True
                node.wave_hold_until = 9999
                node._wave_status = Mock(side_effect=AssertionError('Wave must not override pause'))
                self.assertEqual(node._resolve_candidate('Open_Palm', 0.9, [], 100),
                                 ('Open_Palm', False))
                self.assertFalse(node.wave_latched)


if __name__ == '__main__':
    unittest.main()
