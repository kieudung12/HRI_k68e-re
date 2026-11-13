"""Logic chuyển biểu cảm thành vận tốc, tách khỏi ROS để dễ đọc và kiểm thử."""

import math
import time


EMOTIONS = {'happy', 'sad', 'neutral', 'angry', 'surprise', 'fear'}


class Behavior:
    def __init__(self, timeout=2.0):
        self.timeout = timeout
        self.last_seen = -math.inf
        self.last_label = 'neutral'
        self.active = None
        self.started = 0.0
        self.yaw = None
        self.odom_time = -math.inf
        self.turned = 0.0
        self.status = 'STOP | waiting for face'

    def stop(self, reason):
        self.active = None
        self.status = 'STOP | ' + reason

    def on_yaw(self, yaw, now):
        if self.yaw is not None and self.active == 'surprise':
            # Yaw nhảy từ +pi sang -pi khi đi qua nửa vòng: chuẩn hóa delta.
            delta = math.atan2(math.sin(yaw - self.yaw), math.cos(yaw - self.yaw))
            self.turned += delta
        self.yaw = yaw
        self.odom_time = now

    def on_emotion(self, label, now):
        # Kiểm tra khoảng mất tín hiệu kể cả khi callback tới trước timer.
        if now - self.last_seen > self.timeout:
            self.stop('signal timeout')
        self.last_seen = now
        if label not in EMOTIONS:
            self.stop('no reliable face')
            return
        if label == 'neutral':
            self.last_label = label
            self.stop('neutral')
            return
        if label == self.last_label:
            # Cung trái/phải có thể tiếp tục khi nhận lại mặt sau nhiễu ngắn.
            # Đoạn tiến/lùi và vòng xoay vẫn chỉ chạy một lần mỗi biểu cảm.
            if self.active is not None:
                return
            if label not in {'happy', 'sad'}:
                if 'odom' not in self.status:
                    self.stop('action already used; return to neutral')
                return
        self.last_label = label
        self.stop('changing expression')
        if label == 'surprise' and now - self.odom_time > 0.5:
            self.stop('waiting for odom; return to neutral')
            return
        self.active = label
        self.started = now
        self.turned = 0.0
        self.status = 'RUN | ' + label

    def velocity(self, now):
        if now - self.last_seen > self.timeout:
            self.stop('signal timeout; return to neutral')
        elapsed = now - self.started
        if self.active in {'angry', 'fear'} and elapsed >= 2.0:
            self.stop('step completed; return to neutral')
        if self.active == 'surprise':
            if now - self.odom_time > 0.5:
                self.stop('odom timeout; return to neutral')
            elif self.turned >= 2 * math.pi - 0.03:
                self.stop('360 deg completed; return to neutral')
            elif elapsed > 60.0:
                self.stop('turn timeout; return to neutral')
        return {
            'happy': (0.12, 0.35),
            'sad': (0.12, -0.35),
            'angry': (-0.10, 0.0),
            'fear': (0.10, 0.0),
            'surprise': (0.0, 0.60),
        }.get(self.active, (0.0, 0.0))


class EmotionFilter:
    """EMA làm mượt score; xác nhận nhãn mới và giữ qua nhiễu ngắn tối đa 0.8s."""

    def __init__(self, stable_frames=2, min_confidence=35.0):
        self.required = stable_frames
        self.threshold = min_confidence
        self.reset()

    def reset(self, reason='no_face'):
        self.scores = {}
        self.candidate = None
        self.count = 0
        self.accepted = 'NONE'
        self.last_good = -math.inf
        self.reason = reason

    def update(self, scores, now=None):
        now = time.monotonic() if now is None else now
        if not scores or any(not math.isfinite(float(v)) or not 0 <= float(v) <= 100
                             for v in scores.values()):
            self.reset()
            return 'NONE'
        # Giữ cả disgust/contempt: không ép một nhãn ngoài đề thành lệnh chuyển động.
        self.scores = {
            key: 0.65 * float(value) + 0.35 * self.scores.get(key, float(value))
            for key, value in scores.items()
        }
        label = max(self.scores, key=self.scores.get)
        if label not in EMOTIONS:
            self.accepted, self.candidate, self.count = 'NONE', None, 0
            self.reason = 'unsupported'
            return 'NONE'
        if self.scores[label] < self.threshold:
            self.candidate, self.count = None, 0
            self.reason = 'weak'
        else:
            if label == self.candidate:
                self.count += 1
            else:
                self.candidate, self.count = label, 1
            if self.count >= self.required:
                self.accepted = label
                self.last_good = now
                self.reason = 'accepted'
                return label
            self.reason = 'pending'
        if now - self.last_good <= 0.8:
            return self.accepted
        self.accepted = 'NONE'
        return 'NONE'
