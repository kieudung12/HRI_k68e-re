"""Lấy mẫu mặt thả lỏng và bù thiên lệch của model, không lưu ảnh hay huấn luyện lại."""

import math


class NeutralCalibration:
    def __init__(self):
        self.baseline = None
        self.radius = 12.0
        self.active = False
        self.success = False
        self.message = 'Chưa lấy mẫu mặt bình thường'
        self.samples = []
        self.started = 0.0
        self.first_sample = None

    def start(self, now):
        self.active = True
        self.success = False
        self.samples = []
        self.first_sample = None
        self.started = now
        self.message = 'Giữ mặt thả lỏng, nhìn thẳng camera trong khoảng 3 giây.'

    def clear(self):
        self.__init__()

    def check_timeout(self, now):
        if self.active and now - self.started > 15:
            self.active = False
            self.samples = []
            self.message = 'Chưa lấy đủ mẫu. Nhìn thẳng, đủ sáng rồi bấm lấy mẫu lại.'

    @staticmethod
    def _valid(scores):
        return (bool(scores) and 'neutral' in scores
                and all(math.isfinite(float(v)) and 0 <= v <= 100 for v in scores.values())
                and 95 <= sum(scores.values()) <= 105)

    def process(self, scores, now, captured_at=None):
        self.check_timeout(now)
        if not self._valid(scores):
            if self.active:
                self.samples = []
                self.first_sample = None
                self.message = 'Chưa thấy mặt rõ. Đưa mặt vào khung và giữ thả lỏng.'
            return None
        if self.active:
            # Không lấy frame đang suy luận từ trước lúc người dùng bấm nút.
            if captured_at is not None and captured_at < self.started:
                return None
            if self.first_sample is None:
                self.first_sample = now
            self.samples.append(dict(scores))
            elapsed = now - self.first_sample
            self.message = f'Giữ mặt bình thường: {min(elapsed, 3):.1f}/3 giây · {len(self.samples)} mẫu'
            if elapsed < 3 or len(self.samples) < 12:
                return None
            keys = scores.keys()
            baseline = {key: sum(s.get(key, 0) for s in self.samples)/len(self.samples) for key in keys}
            distances = sorted(sum(abs(s.get(k, 0)-baseline[k]) for k in keys)/2 for s in self.samples)
            spread = distances[int(.9*(len(distances)-1))]
            self.active = False
            self.samples = []
            if spread > 25:
                self.message = 'Biểu cảm thay đổi nhiều lúc lấy mẫu. Thả lỏng mặt và thử lại.'
                return None
            self.baseline = baseline
            self.success = True
            self.radius = min(20.0, max(12.0, spread+3))
            self.message = 'Đã lấy mẫu mặt bình thường cho phiên này.'
        return self.correct(scores)

    def correct(self, scores):
        if not self._valid(scores):
            return None
        if self.baseline is None:
            return dict(scores)
        distance = sum(abs(scores.get(k, 0)-self.baseline.get(k, 0))
                       for k in set(scores) | set(self.baseline))/2
        if distance <= self.radius:
            return {key: 100.0 if key == 'neutral' else 0.0 for key in scores}
        # Chỉ giữ phần tăng so với mặt thả lỏng; Neutral vẫn dùng điểm model.
        adjusted = {key: float(value) if key == 'neutral'
                    else max(0.0, value-self.baseline.get(key, 0)) for key, value in scores.items()}
        total = sum(adjusted.values())
        if total <= 0:
            return None
        return {key: value*100/total for key, value in adjusted.items()}
