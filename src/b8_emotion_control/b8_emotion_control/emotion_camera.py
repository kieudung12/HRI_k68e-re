"""Webcam -> model -> lọc score -> ROS; hiển thị độc lập với suy luận."""

import signal
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

from .behavior import EmotionFilter
from .recognition import Recognizer
from .neutral_calibration import NeutralCalibration


class EmotionCamera(Node):
    def __init__(self):
        super().__init__('emotion_camera')
        for name, value in [('camera', 0), ('detector', 'opencv'), ('classifier', 'hsemotion'),
                            ('stable_frames', 2), ('confidence', 35.0), ('display', True),
                            ('require_calibration', True)]:
            self.declare_parameter(name, value)
        self.backend = self.get_parameter('detector').value
        if self.backend not in {'retinaface', 'opencv'}:
            raise ValueError('detector phải là retinaface hoặc opencv')
        count, threshold = (self.get_parameter(k).value for k in ('stable_frames', 'confidence'))
        if count < 1 or not 0 <= threshold <= 100:
            raise ValueError('stable_frames >= 1; confidence trong [0, 100]')
        self.filter = EmotionFilter(count, threshold)
        self.calibration = NeutralCalibration()
        self.require_calibration = self.get_parameter('require_calibration').value
        self.raw_prediction = None
        self.paused_before_calibration = False
        self.display = self.get_parameter('display').value
        self.publisher = self.create_publisher(String, '/detected_emotion', 1)
        self.state_sub = self.create_subscription(String, '/emotion_robot_state', self.on_state, 1)
        self.state, self.state_time = 'STOP | waiting', -float('inf')
        self.caption = 'Loading / waiting for inference'
        self.hint = 'Nhìn thẳng camera, giữ mặt trong khung hình và đủ ánh sáng.'
        self.region, self.accepted, self.paused = None, 'NONE', False
        self.result_time = -float('inf')
        self.running, self.future, self.submitted_at = True, None, 0.0
        self.inference_ms = 0.0
        self.fps, self.frames, self.fps_time = 0.0, 0, time.monotonic()
        self.get_logger().info('Dang nap model bieu cam...')
        self.recognizer = Recognizer(self.backend, self.get_parameter('classifier').value)
        self.cap = cv2.VideoCapture(self.get_parameter('camera').value)
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError('Khong mo duoc webcam; thu camera:=1')
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.pool = ThreadPoolExecutor(max_workers=1)
        if self.display:
            from .camera_view import CameraView
            self.ui = CameraView(self.request_stop, self.toggle_pause, self.set_threshold, threshold,
                                 on_calibrate=self.start_calibration, on_clear=self.clear_calibration)
            self.window = self.ui.window
        self.create_timer(1 / 30, self.tick)
        self.get_logger().info('Camera san sang. Space: tam dung. Q / Esc: dong.')

    def on_state(self, message):
        self.state, self.state_time = message.data, time.monotonic()

    def request_stop(self, event=None):
        self.running = False

    def set_threshold(self, value):
        self.filter.threshold = value

    def toggle_pause(self):
        if self.calibration.active:
            return
        if self.require_calibration and self.calibration.baseline is None:
            self.start_calibration()
            return
        self.paused = not self.paused
        self.filter.reset()
        self.accepted = 'NONE'
        self.publisher.publish(String(data='NONE'))

    def start_calibration(self):
        if not self.calibration.active:
            self.paused_before_calibration = self.paused
        self.paused = True
        self.accepted = 'NONE'
        self.filter.reset('calibrating')
        self.calibration.start(time.monotonic())
        self.hint = self.calibration.message
        self.publisher.publish(String(data='NONE'))

    def clear_calibration(self):
        self.calibration.clear()
        self.paused = True
        self.filter.reset()
        self.accepted = 'NONE'
        self.hint = 'Đã xóa mẫu. Lấy mẫu lại hoặc bấm Tiếp tục để dùng điểm model gốc.'
        self.publisher.publish(String(data='NONE'))

    def accept_result(self, now):
        error = None
        try:
            face = self.future.result()
        except Exception as exception:
            self.get_logger().error(f'Loi suy luan: {exception}')
            error, face = exception, None
        self.inference_ms = (now - self.submitted_at) * 1000
        self.region, scores = None, None
        if now - self.submitted_at > 1.5:
            self.hint = 'Xử lý ảnh đang chậm. Thử đóng bớt ứng dụng nặng.'
        elif error:
            self.hint = 'Model gặp lỗi; xem thông báo trong terminal.'
        elif face is None:
            self.hint = 'Chưa thấy mặt. Nhìn thẳng camera và đưa mặt vào giữa khung hình.'
        else:
            self.region, scores = face['region'], face['emotion']
            self.hint = ('Đưa mặt lại gần camera hơn.' if face.get('small_face')
                         else 'Ánh sáng yếu. Chiếu sáng phía trước mặt, tránh ngược sáng.'
                         if face.get('brightness', 100) < 55 else '')
        self.raw_prediction = ((max(scores, key=scores.get), max(scores.values())) if scores else None)
        was_calibrating = self.calibration.active
        corrected = self.calibration.process(scores, now, captured_at=self.submitted_at)
        if was_calibrating and not self.calibration.active:
            self.filter.reset()
            self.paused = self.paused_before_calibration if self.calibration.success else True
            self.hint = self.calibration.message
        elif self.calibration.active:
            self.hint = self.calibration.message
        self.accepted = self.filter.update(corrected, now)
        if self.require_calibration and self.calibration.baseline is None:
            self.accepted = 'NONE'
            self.filter.reset('needs_calibration')
            if not self.calibration.active:
                self.hint = 'Bước đầu: thả lỏng mặt rồi bấm Lấy mẫu Bình thường để bắt đầu.'
        if scores:
            label = max(scores, key=scores.get)
            self.caption = f'{label.upper()} {scores[label]:.1f}% | accepted: {self.accepted}'
            if not self.hint:
                self.hint = {
                    'accepted': 'Đã nhận biểu cảm. Bạn có thể đổi trực tiếp sang biểu cảm khác.',
                    'pending': 'Đang xác nhận biểu cảm mới. Giữ thêm một chút.',
                    'weak': 'Biểu cảm chưa rõ. Thử rõ hơn hoặc giảm ngưỡng bằng thanh bên phải.',
                    'unsupported': 'Model nghiêng về Ghê tởm; biểu cảm này không có lệnh trong bài.',
                }.get(self.filter.reason, 'Giữ biểu cảm trong một lúc để xác nhận.')
        else:
            self.caption = 'NO FACE / no fresh inference | accepted: NONE'
        self.publisher.publish(String(data='NONE' if self.paused else self.accepted))
        self.result_time = now

    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            self.publisher.publish(String(data='NONE'))
            self.get_logger().error('Mat ket noi webcam; dung node.')
            self.running = False
            return
        now = time.monotonic()
        was_calibrating = self.calibration.active
        self.calibration.check_timeout(now)
        if was_calibrating and not self.calibration.active:
            self.paused = True
            self.filter.reset()
            self.accepted = 'NONE'
            self.hint = self.calibration.message
            self.publisher.publish(String(data='NONE'))
        self.frames += 1
        if now - self.fps_time >= 1:
            self.fps = self.frames / (now - self.fps_time)
            self.frames, self.fps_time = 0, now
        if self.future is not None and self.future.done():
            self.accept_result(now)
            self.future = None
        if now - self.result_time > 1.5 and self.accepted != 'NONE':
            self.filter.reset('stale')
            self.accepted, self.region = 'NONE', None
            self.hint = 'Chưa có kết quả mới. Robot đã dừng.'
            self.publisher.publish(String(data='NONE'))
        if self.future is None and now - self.submitted_at >= 0.12:
            self.submitted_at = now
            self.future = self.pool.submit(self.recognizer.analyze, frame.copy())
        if self.display:
            self.ui.render(frame, region=self.region, scores=self.filter.scores,
                           accepted=self.accepted, hint=self.hint, state=self.state,
                           connected=now-self.state_time < 2, fps=self.fps,
                           latency=self.inference_ms, paused=self.paused,
                           progress=self.filter.count, required=self.filter.required,
                           calibrating=self.calibration.active,
                           calibrated=self.calibration.baseline is not None,
                           calibration_note=self.calibration.message,
                           raw_prediction=self.raw_prediction,
                           needs_calibration=self.require_calibration and self.calibration.baseline is None)

    def close(self):
        if rclpy.ok():
            self.publisher.publish(String(data='NONE'))
        self.cap.release()
        if self.display:
            self.ui.close()
        self.pool.shutdown(wait=True, cancel_futures=True)


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = None
    try:
        node = EmotionCamera()
        while rclpy.ok() and node.running:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if node is not None:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
