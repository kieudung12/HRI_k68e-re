"""Sequential Nav2 goals with concurrent YOLO inference on the RGB stream."""
import math
from pathlib import Path
import threading
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Image
import yaml

from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


class YoloCameraNode(Node):
    """Subscribe to RGB images, run YOLO, publish an annotated image, and log labels."""

    def __init__(self):
        super().__init__('b5_yolo_camera')
        self.declare_parameter('image_topic', '/oakd/rgb/preview/image_raw')
        self.declare_parameter('annotated_topic', '/yolo/detections/image')
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.20)
        self.declare_parameter('inference_period', 0.5)
        self.declare_parameter('display', False)
        self.bridge = CvBridge()
        self.display = bool(self.get_parameter('display').value)
        self.last_inference = 0.0
        self.window_created = False
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        self.model = None
        try:
            from ultralytics import YOLO
            model_path = str(self.get_parameter('model').value)
            self.get_logger().info(f'Loading YOLO model: {model_path}')
            self.model = YOLO(model_path)
            self.get_logger().info('YOLO model is ready.')
        except Exception as exc:
            self.get_logger().error(
                f'Could not load YOLO model ({exc}); navigation will still run, '
                'but install ultralytics and check model access to enable detection.')

        image_topic = str(self.get_parameter('image_topic').value)
        annotated_topic = str(self.get_parameter('annotated_topic').value)
        self.publisher = self.create_publisher(Image, annotated_topic, 10)
        self.subscription = self.create_subscription(
            Image, image_topic, self.image_callback, qos_profile_sensor_data)
        self.get_logger().info(
            f'Listening on {image_topic}; annotated images publish on {annotated_topic}.')

    def image_callback(self, msg):
        if self.model is None:
            return
        now = time.monotonic()
        period = max(0.05, float(self.get_parameter('inference_period').value))
        if now - self.last_inference < period:
            return
        self.last_inference = now
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            result = self.model.predict(
                source=frame,
                conf=float(self.get_parameter('confidence').value),
                verbose=False,
            )[0]
            annotated = result.plot()
            out_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            out_msg.header = msg.header
            self.publisher.publish(out_msg)
            if self.display:
                with self.frame_lock:
                    self.latest_frame = annotated

            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                self.get_logger().info('YOLO: no objects detected in this frame.')
            else:
                names = result.names
                labels = []
                for box in boxes:
                    class_id = int(box.cls.item())
                    confidence = float(box.conf.item())
                    label = f'{names[class_id]} ({confidence:.2f})'
                    labels.append(label)
                self.get_logger().info('YOLO detections: ' + ', '.join(labels))
        except Exception as exc:
            self.get_logger().error(f'Image inference failed: {exc}')

    def show_latest_frame(self):
        """Run OpenCV's GUI event loop exclusively on the main thread."""
        if not self.display:
            return
        with self.frame_lock:
            frame = self.latest_frame
        if frame is None:
            return
        import cv2
        window_name = 'TurtleBot 4 YOLO detections'
        if not self.window_created:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 960, 720)
            self.window_created = True
        cv2.imshow(window_name, frame)
        cv2.waitKey(1)

    def close_window(self):
        if self.window_created:
            import cv2
            cv2.destroyWindow('TurtleBot 4 YOLO detections')


def load_goals(path):
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    goals = data.get('goals', []) if isinstance(data, dict) else []
    if len(goals) < 3:
        raise ValueError(f'Expected at least three goals in {path}')
    for goal in goals:
        for field in ('x', 'y', 'yaw'):
            if field not in goal or not math.isfinite(float(goal[field])):
                raise ValueError(f'Invalid {field} value in goal: {goal}')
    return goals


def make_pose(navigator, goal):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = float(goal['x'])
    pose.pose.position.y = float(goal['y'])
    pose.pose.orientation.z = math.sin(float(goal['yaw']) / 2.0)
    pose.pose.orientation.w = math.cos(float(goal['yaw']) / 2.0)
    return pose


def navigate_goals(navigator, goals_file, stop_requested, navigation_done):
    """Run blocking Commander calls without blocking the desktop event loop."""
    try:
        goals = load_goals(goals_file)
        navigator.get_logger().info(
            'Waiting for AMCL initial pose and active Nav2 lifecycle nodes. '
            'Set the initial pose in RViz and wait for the laser scan to align.')
        navigator.waitUntilNav2Active()

        for index, goal in enumerate(goals, start=1):
            if stop_requested.is_set():
                return
            name = str(goal.get('name', f'Goal {index}'))
            navigator.get_logger().info(
                f'Sending {name}: x={float(goal["x"]):.2f}, '
                f'y={float(goal["y"]):.2f}, yaw={float(goal["yaw"]):.2f} rad')
            navigator.goToPose(make_pose(navigator, goal))
            while not navigator.isTaskComplete():
                if stop_requested.is_set():
                    navigator.cancelTask()
                    navigator.get_logger().warn('Interrupted; current navigation task canceled.')
                    return
                time.sleep(0.1)
            result = navigator.getResult()
            if result == TaskResult.SUCCEEDED:
                navigator.get_logger().info(f'{name} reached successfully.')
            else:
                navigator.get_logger().error(
                    f'{name} did not succeed (Nav2 result: {result}); stopping goal sequence.')
                break
    except Exception as exc:
        if not stop_requested.is_set() and rclpy.ok():
            navigator.get_logger().error(f'Autonomous navigation stopped: {exc}')
    finally:
        navigation_done.set()


def main(args=None):
    # HighGUI stays on the main thread; ROS inference and blocking Nav2
    # calls run separately so the camera remains visible while Nav2 waits.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    camera = YoloCameraNode()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(camera)
    camera_thread = threading.Thread(target=executor.spin, daemon=True)
    camera_thread.start()

    navigator = BasicNavigator()
    goals_file = get_package_share_directory('b5_tb4_lab') + '/config/goals.yaml'
    stop_requested = threading.Event()
    navigation_done = threading.Event()
    navigation_thread = threading.Thread(
        target=navigate_goals,
        args=(navigator, goals_file, stop_requested, navigation_done),
        daemon=True,
    )
    navigation_thread.start()
    try:
        while rclpy.ok() and not navigation_done.is_set():
            camera.show_latest_frame()
            time.sleep(0.02)
    except KeyboardInterrupt:
        stop_requested.set()
    finally:
        stop_requested.set()
        # Allow a live goal to be canceled. Context shutdown releases a
        # lifecycle-service wait if Nav2 has not started yet.
        navigation_thread.join(timeout=3.0)
        executor.shutdown(timeout_sec=2.0)
        camera_thread.join(timeout=2.0)
        camera.close_window()
        if rclpy.ok():
            rclpy.shutdown()
        navigation_thread.join(timeout=2.0)
        camera.destroy_node()
        navigator.destroy_node()


if __name__ == '__main__':
    main()
