#!/usr/bin/env python3
"""Webcam + MediaPipe Gesture Recognizer ROS 2 node."""

from __future__ import annotations

from collections import deque
from pathlib import Path
import time
import urllib.request

import cv2
import mediapipe as mp
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


MODEL_URL = (
    'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/'
    'gesture_recognizer/float16/1/gesture_recognizer.task'
)
LABELS = {
    'Open_Palm': 'Open Palm', 'Closed_Fist': 'Closed Fist',
    'Pointing_Up': 'Pointing Up', 'Victory': 'Victory',
    'Thumb_Up': 'Thumbs Up',
}
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
]
FINGERTIP_IDS = (4, 8, 12, 16, 20)
FINGER_COLORS = {
    0: (90, 205, 250), 1: (100, 230, 180), 2: (245, 210, 100),
    3: (220, 140, 250), 4: (100, 175, 255),
}


def draw_hand(frame, landmarks) -> None:
    """Draw the 21 hand keypoints, colored finger bones, and fingertip IDs."""
    height, width = frame.shape[:2]
    points = [(int(p.x * width), int(p.y * height)) for p in landmarks]
    finger_for_connection = {
        (0, 1): 0, (1, 2): 0, (2, 3): 0, (3, 4): 0,
        (0, 5): 1, (5, 6): 1, (6, 7): 1, (7, 8): 1,
        (5, 9): 2, (9, 10): 2, (10, 11): 2, (11, 12): 2,
        (9, 13): 3, (13, 14): 3, (14, 15): 3, (15, 16): 3,
        (13, 17): 4, (17, 18): 4, (18, 19): 4, (19, 20): 4,
        (0, 17): 4,
    }
    for connection in HAND_CONNECTIONS:
        start, end = connection
        color = FINGER_COLORS[finger_for_connection[connection]]
        cv2.line(frame, points[start], points[end], (18, 25, 27), 7, cv2.LINE_AA)
        cv2.line(frame, points[start], points[end], color, 3, cv2.LINE_AA)
    for index, point in enumerate(points):
        radius = 7 if index in FINGERTIP_IDS else 4
        cv2.circle(frame, point, radius + 2, (18, 25, 27), -1, cv2.LINE_AA)
        cv2.circle(frame, point, radius, (242, 249, 245), -1, cv2.LINE_AA)
        if index in FINGERTIP_IDS:
            cv2.putText(frame, str(index), (point[0] + 7, point[1] - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (248, 252, 250),
                        1, cv2.LINE_AA)


def draw_dashboard(frame, detected, score, stable, stable_count, required,
                   robot_status, fps, hand_present):
    """Compact camera HUD for recognition, confidence, debounce, and robot state."""
    height, width = frame.shape[:2]
    panel_width = min(420, width - 36)
    panel_height = min(218, height - 36)
    x0, y0 = 18, 18
    x1, y1 = x0 + panel_width, y0 + panel_height
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (19, 27, 29), -1)
    cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (74, 99, 94), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (x0, y0), (x0 + 5, y1), (91, 221, 180), -1)

    left = x0 + 20
    cv2.putText(frame, 'B6  /  HAND GESTURE CONTROL', (left, y0 + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.54, (234, 243, 239), 1, cv2.LINE_AA)
    cv2.circle(frame, (x1 - 58, y0 + 22), 5, (83, 230, 163), -1, cv2.LINE_AA)
    cv2.putText(frame, 'LIVE', (x1 - 47, y0 + 27), cv2.FONT_HERSHEY_SIMPLEX,
                0.40, (153, 221, 193), 1, cv2.LINE_AA)

    cv2.putText(frame, 'DETECTED GESTURE', (left, y0 + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (149, 171, 165), 1, cv2.LINE_AA)
    gesture_text = detected.upper().replace('_', ' ') if detected else 'NO HAND'
    cv2.putText(frame, gesture_text, (left, y0 + 93),
                cv2.FONT_HERSHEY_SIMPLEX, 0.82, (244, 250, 247), 2, cv2.LINE_AA)
    cv2.putText(frame, f'{score:.0%}', (x1 - 75, y0 + 91),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (110, 229, 185), 2, cv2.LINE_AA)

    bar_x, bar_y, bar_w, bar_h = left, y0 + 108, panel_width - 42, 7
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                  (50, 66, 64), -1)
    cv2.rectangle(frame, (bar_x, bar_y),
                  (bar_x + int(bar_w * max(0.0, min(1.0, score))), bar_y + bar_h),
                  (91, 221, 180), -1)

    cv2.putText(frame, 'STABILITY', (left, y0 + 143),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (149, 171, 165), 1, cv2.LINE_AA)
    cv2.putText(frame, f'{stable_count:02d} / {required:02d}', (x1 - 90, y0 + 143),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (226, 239, 233), 1, cv2.LINE_AA)
    cv2.putText(frame, stable.upper().replace('_', ' ') if stable != 'NONE' else 'WAITING FOR STABLE POSE',
                (left, y0 + 165), cv2.FONT_HERSHEY_SIMPLEX, 0.43,
                (110, 229, 185) if stable != 'NONE' else (172, 185, 180), 1, cv2.LINE_AA)

    status = robot_status[:39]
    cv2.putText(frame, 'ROBOT', (left, y0 + 195),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (149, 171, 165), 1, cv2.LINE_AA)
    cv2.putText(frame, status, (left + 59, y0 + 195),
                cv2.FONT_HERSHEY_SIMPLEX, 0.39, (236, 224, 151), 1, cv2.LINE_AA)

    stats = f'{fps:4.1f} FPS  |  {"21 KEYPOINTS" if hand_present else "NO HAND"}'
    (text_w, _), _ = cv2.getTextSize(stats, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    sx, sy = width - text_w - 22, 51
    cv2.putText(frame, stats, (sx, sy), cv2.FONT_HERSHEY_SIMPLEX,
                0.42, (224, 239, 233), 1, cv2.LINE_AA)
    cv2.putText(frame, 'UP: SELECT   VICTORY: CIRCLE   WAVE: GREET   THUMB: START/RESUME   PALM: PAUSE   FIST: CANCEL',
                (18, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                (235, 242, 238), 1, cv2.LINE_AA)
    cv2.putText(frame, 'Q: QUIT', (width - 83, 22), cv2.FONT_HERSHEY_SIMPLEX,
                0.36, (213, 227, 221), 1, cv2.LINE_AA)


def model_file() -> Path:
    path = Path.home() / '.cache' / 'b6_gesture_control' / 'gesture_recognizer.task'
    if path.is_file() and path.stat().st_size > 1_000_000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.download')
    request = urllib.request.Request(MODEL_URL, headers={'User-Agent': 'b6-gesture-control/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if temporary.stat().st_size <= 1_000_000:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('MediaPipe model download is incomplete.')
    temporary.replace(path)
    return path


class GestureRecognitionNode(Node):
    """Publishes a debounced gesture heartbeat and displays recognition confidence."""

    def __init__(self) -> None:
        super().__init__('gesture_recognition_node')
        self.declare_parameter('camera_index', 0)
        self.declare_parameter('stable_frames', 3)
        self.declare_parameter('min_confidence', 0.60)
        self.declare_parameter('display', True)
        self.declare_parameter('model_path', '')
        self.publisher = self.create_publisher(String, '/detected_gesture', 10)
        self.robot_status = 'WAITING FOR GESTURE NODE'
        self.status_subscription = self.create_subscription(
            String, '/robot_behavior_state', self._on_robot_status, 1
        )
        self.camera_index = self.get_parameter('camera_index').value
        self.stable_frames = max(1, int(self.get_parameter('stable_frames').value))
        self.min_confidence = float(self.get_parameter('min_confidence').value)
        self.display = bool(self.get_parameter('display').value)
        configured_path = self.get_parameter('model_path').value
        self.model_path = Path(configured_path).expanduser() if configured_path else model_file()
        self.history: deque[str | None] = deque(maxlen=self.stable_frames)
        # Keep enough samples for a natural wave at both 30 and 60 FPS.
        self.positions: deque[tuple[float, float]] = deque(maxlen=120)

    def _on_robot_status(self, message: String) -> None:
        self.robot_status = message.data

    @staticmethod
    def _gesture(result) -> tuple[str | None, float]:
        if not result.gestures or not result.gestures[0]:
            return None, 0.0
        top = max(result.gestures[0], key=lambda category: category.score or 0.0)
        return top.category_name, float(top.score or 0.0)

    def _wave_status(self, landmarks, now: float) -> tuple[bool, bool]:
        if not landmarks:
            self.positions.clear()
            return False, False
        # Track palm center. Require an open palm and a clear left-right reversal,
        # and scale the motion threshold to the visible palm size so a small wrist
        # shake still counts when the hand is close to or far from the camera.
        center_x = sum(landmarks[i].x for i in (0, 5, 9, 13, 17)) / 5.0
        palm_width = abs(landmarks[5].x - landmarks[17].x)
        moving_threshold = max(0.012, palm_width * 0.12)
        wave_threshold = max(0.018, palm_width * 0.18)
        self.positions.append((now, center_x))
        recent = [(t, x) for t, x in self.positions if now - t <= 1.0]
        recent_motion = [(t, x) for t, x in recent if now - t <= 0.35]
        moving = (
            len(recent_motion) >= 2
            and max(x for _, x in recent_motion) - min(x for _, x in recent_motion) >= moving_threshold
        )
        if len(recent) < 4:
            return False, moving
        # Measure complete strokes between extrema, not per-frame velocity.
        # Each stroke must travel wave_threshold before a reversal counts;
        # this rejects jitter and works for slow waves at different frame rates.
        anchor = extreme = recent[0][1]
        direction = 0
        for _, x in recent[1:]:
            if direction == 0:
                if abs(x - anchor) >= wave_threshold:
                    direction = 1 if x > anchor else -1
                    extreme = x
            elif direction > 0:
                extreme = max(extreme, x)
                if extreme - x >= wave_threshold:
                    return True, moving
            else:
                extreme = min(extreme, x)
                if x - extreme >= wave_threshold:
                    return True, moving
        return False, moving

    def _publish(self, label: str) -> None:
        message = String()
        message.data = label
        self.publisher.publish(message)

    def _resolve_candidate(self, raw, score, landmarks, now):
        candidate = raw if raw in LABELS and score >= self.min_confidence else None
        moving = False
        if candidate != 'Open_Palm':
            self.positions.clear()
            return candidate, moving
        # Once an action is retained, an open palm is always the pause command.
        # Motion/latching for selecting Wave must never hide that command.
        if self.robot_status.startswith(('RUNNING |', 'PAUSED |')):
            self.positions.clear()
            return 'Open_Palm', moving
        # The behavior node already retains this selection. Use its state as the
        # single source of truth rather than maintaining a second Wave latch.
        if self.robot_status.startswith('SELECTED | GREETING'):
            self.positions.clear()
            return 'Wave', moving
        waving, moving = self._wave_status(landmarks, now)
        if waving:
            candidate = 'Wave'
        elif moving:
            candidate = None
        return candidate, moving

    def _debounce(self, candidate):
        self.history.append(candidate)
        count = 0
        for item in reversed(self.history):
            if candidate is None or item != candidate:
                break
            count += 1
        required = min(self.stable_frames, 2) if candidate == 'Wave' else self.stable_frames
        stable = candidate if candidate is not None and count >= required else 'NONE'
        return stable, min(count, required), required

    def run_camera(self) -> None:
        if not self.model_path.is_file():
            raise FileNotFoundError(f'MediaPipe task file not found: {self.model_path}')
        capture = cv2.VideoCapture(self.camera_index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f'Cannot open webcam index {self.camera_index}.')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        recognizer = None
        try:
            options = mp.tasks.vision.GestureRecognizerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.45,
                min_hand_presence_confidence=0.45,
                min_tracking_confidence=0.45,
            )
            recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
            last_timestamp = 0
            camera_error_reported = False
            previous_frame_time = time.monotonic()
            fps = 0.0
            self.get_logger().info('Webcam ready; publishing /detected_gesture.')
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.0)
                ok, frame = capture.read()
                if not ok:
                    self.history.clear()
                    self.positions.clear()
                    if not camera_error_reported:
                        self.get_logger().warning('Could not read webcam frame; stopping command heartbeat.')
                        camera_error_reported = True
                    time.sleep(0.1)
                    continue
                camera_error_reported = False
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp = max(time.monotonic_ns() // 1_000_000, last_timestamp + 1)
                last_timestamp = timestamp
                result = recognizer.recognize_for_video(image, timestamp)
                current_time = time.monotonic()
                frame_period = current_time - previous_frame_time
                if frame_period > 0:
                    instantaneous_fps = 1.0 / frame_period
                    fps = instantaneous_fps if fps == 0.0 else 0.85 * fps + 0.15 * instantaneous_fps
                previous_frame_time = current_time
                raw, score = self._gesture(result)
                landmarks = result.hand_landmarks[0] if result.hand_landmarks else None
                candidate, moving_open_palm = self._resolve_candidate(
                    raw, score, landmarks, current_time,
                )
                stable, stable_count, required_frames = self._debounce(candidate)
                # Publish continuously while stable so the behavior node can detect lost control.
                self._publish(stable)

                if landmarks:
                    draw_hand(frame, landmarks)
                visible = (
                    'Wave' if candidate == 'Wave'
                    else 'Waving...' if moving_open_palm
                    else LABELS.get(raw, raw)
                )
                draw_dashboard(
                    frame, visible, score, stable, stable_count,
                    required_frames, self.robot_status, fps, bool(landmarks),
                )
                if self.display:
                    cv2.imshow('B6 TurtleBot 4 Hand Gestures', frame)
                    if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q'), 27):
                        break
        finally:
            if rclpy.ok():
                self._publish('NONE')
            if recognizer is not None:
                recognizer.close()
            capture.release()
            if self.display:
                cv2.destroyAllWindows()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = GestureRecognitionNode()
        node.run_camera()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        if node is not None:
            node.get_logger().error(str(error))
        else:
            print(f'Could not start gesture recognizer: {error}')
        raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
