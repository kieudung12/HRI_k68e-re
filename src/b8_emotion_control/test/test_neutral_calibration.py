import math
import unittest

from b8_emotion_control.behavior import EmotionFilter
from b8_emotion_control.neutral_calibration import NeutralCalibration


class NeutralCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.c = NeutralCalibration()
        # Mặt thả lỏng bị model gốc nghiêng về Sad.
        self.rest = {'sad': 70.0, 'neutral': 20.0, 'angry': 5.0, 'happy': 5.0,
                     'fear': 0.0, 'surprise': 0.0, 'disgust': 0.0}

    def fit(self):
        self.c.start(0)
        for i in range(17):
            result = self.c.process(self.rest, i*.2, i*.2)
        self.assertFalse(self.c.active)
        return result

    def test_rest_bias_becomes_neutral_and_small_jitter_stays_neutral(self):
        result = self.fit()
        self.assertEqual(max(result, key=result.get), 'neutral')
        jitter = {**self.rest, 'sad': 76., 'neutral': 14.}
        self.assertEqual(self.c.correct(jitter)['neutral'], 100)

    def test_actual_sad_increase_is_not_always_replaced_by_neutral(self):
        self.fit()
        sad = {**dict.fromkeys(self.rest, 0.), 'sad': 95., 'neutral': 5.}
        result = self.c.correct(sad)
        self.assertEqual(max(result, key=result.get), 'sad')

    def test_happy_and_unsupported_disgust_remain_distinguishable(self):
        self.fit()
        for label in ['happy', 'disgust', 'angry', 'surprise', 'fear']:
            result = self.c.correct({**dict.fromkeys(self.rest, 0.), label: 90., 'neutral': 10.})
            self.assertEqual(max(result, key=result.get), label)

    def test_no_output_during_collection_and_old_frame_is_ignored(self):
        self.c.start(1)
        self.assertIsNone(self.c.process(self.rest, 1.1, .9))
        self.assertFalse(self.c.samples)
        for i in range(10):
            self.assertIsNone(self.c.process(self.rest, 1.2+i*.1, 1.2+i*.1))
        self.assertTrue(self.c.active)

    def test_face_loss_restarts_collection_and_stays_no_face_after_fit(self):
        self.c.start(0)
        self.c.process(self.rest, 0)
        self.assertIsNone(self.c.process(None, .5))
        self.assertFalse(self.c.samples)
        self.fit()
        self.assertIsNone(self.c.process(None, 4))
        self.assertIsNone(self.c.process({'neutral': math.nan}, 4))

    def test_timeout_and_clear_do_not_create_a_neutral_profile(self):
        self.c.start(0)
        self.c.check_timeout(16)
        self.assertFalse(self.c.active)
        self.assertIsNone(self.c.baseline)
        self.fit()
        self.c.clear()
        self.assertIsNone(self.c.baseline)
        self.assertEqual(self.c.correct(self.rest), self.rest)

    def test_unstable_collection_does_not_replace_a_good_profile(self):
        self.fit()
        baseline = dict(self.c.baseline)
        self.c.start(4)
        for i in range(16):
            label = 'happy' if i % 2 else 'sad'
            self.c.process({**dict.fromkeys(self.rest, 0.), label: 100.}, 4+i*.2)
        self.assertFalse(self.c.active)
        self.assertFalse(self.c.success)
        self.assertEqual(self.c.baseline, baseline)

    def test_calibrated_filter_changes_neutral_to_sad_and_back(self):
        self.fit()
        f = EmotionFilter()
        for i in range(5): result = f.update(self.c.correct(self.rest), i*.2)
        self.assertEqual(result, 'neutral')
        sad = {**dict.fromkeys(self.rest, 0.), 'sad': 95., 'neutral': 5.}
        for i in range(5): result = f.update(self.c.correct(sad), 1+i*.2)
        self.assertEqual(result, 'sad')
        for i in range(5): result = f.update(self.c.correct(self.rest), 2+i*.2)
        self.assertEqual(result, 'neutral')


if __name__ == '__main__':
    unittest.main()
