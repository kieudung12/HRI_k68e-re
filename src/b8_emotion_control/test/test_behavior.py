import math
import unittest

from b8_emotion_control.behavior import Behavior, EmotionFilter


class BehaviorTests(unittest.TestCase):
    def test_mapping_and_neutral(self):
        for label, expected in [('happy', (0.12, 0.35)), ('sad', (0.12, -0.35)),
                                ('angry', (-0.10, 0.0)), ('fear', (0.10, 0.0)),
                                ('surprise', (0.0, 0.60))]:
            with self.subTest(label=label):
                b = Behavior()
                b.on_yaw(0, 0)
                b.on_emotion(label, 0)
                self.assertEqual(b.velocity(0.1), expected)
                b.on_emotion('neutral', 0.2)
                self.assertEqual(b.velocity(0.2), (0, 0))

    def test_short_step_does_not_repeat_while_expression_held(self):
        for label in ['angry', 'fear']:
            b = Behavior()
            b.on_emotion(label, 0)
            b.on_emotion(label, 1)
            b.on_emotion(label, 2)
            self.assertEqual(b.velocity(2), (0, 0))
            b.on_emotion(label, 3)
            self.assertEqual(b.velocity(3), (0, 0))
            b.on_emotion('neutral', 3.1)
            b.on_emotion(label, 3.2)
            self.assertNotEqual(b.velocity(3.2), (0, 0))

    def test_arc_resumes_only_after_a_new_valid_expression_message(self):
        b = Behavior()
        b.on_emotion('happy', 0)
        self.assertEqual(b.velocity(2.1), (0, 0))
        b.on_emotion('happy', 2.2)
        self.assertEqual(b.velocity(2.2), (0.12, 0.35))
        # Khoảng mất tín hiệu cũng phải được phát hiện trước callback mới.
        b = Behavior()
        b.on_emotion('happy', 0)
        b.on_emotion('happy', 3)
        self.assertEqual(b.velocity(3), (0.12, 0.35))

    def test_short_action_cannot_repeat_after_signal_gap(self):
        b = Behavior()
        b.on_emotion('fear', 0)
        b.on_emotion('fear', 3)
        self.assertEqual(b.velocity(3), (0, 0))

    def test_unreliable_input_stops_without_rearming(self):
        b = Behavior()
        b.on_emotion('fear', 0)
        b.on_emotion('NONE', 0.1)
        self.assertEqual(b.velocity(0.1), (0, 0))
        b.on_emotion('fear', 0.2)
        self.assertEqual(b.velocity(0.2), (0, 0))
        self.assertIn('return to neutral', b.status)
        b.on_emotion('happy', 0.3)
        self.assertEqual(b.velocity(0.3), (0.12, 0.35))

    def test_turn_one_revolution_across_yaw_wrap(self):
        b = Behavior()
        start = 3.0
        b.on_yaw(start, 0)
        b.on_emotion('surprise', 0)
        for i in range(1, 65):
            t = i * 0.1
            angle = start + i * 0.1
            b.on_yaw(math.atan2(math.sin(angle), math.cos(angle)), t)
            b.on_emotion('surprise', t)
            command = b.velocity(t)
            if i < 62:
                self.assertEqual(command, (0, 0.6))
        self.assertEqual(command, (0, 0))
        b.on_emotion('surprise', 6.5)
        self.assertEqual(b.velocity(6.5), (0, 0))

    def test_turn_requires_fresh_odom_and_stops_if_lost(self):
        b = Behavior()
        b.on_emotion('surprise', 0)
        self.assertEqual(b.velocity(0), (0, 0))
        b.on_emotion('neutral', 0.1)
        b.on_yaw(0, 0.2)
        b.on_emotion('surprise', 0.2)
        self.assertEqual(b.velocity(0.2), (0, 0.6))
        self.assertEqual(b.velocity(0.8), (0, 0))

    def test_turn_has_time_limit_even_if_odom_does_not_move(self):
        b = Behavior()
        b.on_yaw(0, 0)
        b.on_emotion('surprise', 0)
        b.on_yaw(0, 60.1)
        b.on_emotion('surprise', 60.1)
        self.assertEqual(b.velocity(60.1), (0, 0))


class FilterTests(unittest.TestCase):
    @staticmethod
    def scores(**values):
        result = dict.fromkeys(['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise'], 0.0)
        result.update(values)
        return result

    def test_confirm_then_change_without_interrupting_for_one_noisy_result(self):
        f = EmotionFilter()
        happy = self.scores(happy=90, neutral=10)
        sad = self.scores(sad=90, neutral=10)
        self.assertEqual(f.update(happy, 0), 'NONE')
        self.assertEqual(f.update(happy, .2), 'happy')
        self.assertEqual(f.update(sad, .4), 'happy')
        self.assertEqual(f.update(happy, .6), 'happy')
        self.assertEqual(f.update(sad, .8), 'happy')
        self.assertEqual(f.update(sad, 1.0), 'sad')

    def test_weak_signal_is_held_briefly_but_not_indefinitely(self):
        f = EmotionFilter(min_confidence=60)
        strong = self.scores(happy=90, neutral=10)
        weak = self.scores(happy=35, neutral=34, sad=31)
        f.update(strong, 0)
        f.update(strong, .2)
        self.assertEqual(f.update(weak, .4), 'happy')
        self.assertEqual(f.update(weak, .8), 'happy')
        self.assertEqual(f.update(weak, 1.2), 'NONE')

    def test_face_loss_clears_smoothing_and_requires_confirmation_again(self):
        f = EmotionFilter()
        happy = self.scores(happy=100)
        f.update(happy, 0)
        f.update(happy, .2)
        self.assertEqual(f.update(None, .3), 'NONE')
        self.assertFalse(f.scores)
        self.assertEqual(f.update(happy, .4), 'NONE')
        self.assertEqual(f.update(happy, .6), 'happy')

    def test_disgust_and_invalid_scores_stop_immediately(self):
        f = EmotionFilter(stable_frames=1)
        self.assertEqual(f.update(self.scores(happy=100), 0), 'happy')
        self.assertEqual(f.update(self.scores(disgust=100), .1), 'NONE')
        for scores in [{}, {'happy': math.nan}, {'happy': 120}]:
            self.assertEqual(f.update(scores, .2), 'NONE')

    def test_threshold_does_not_force_the_runner_up_to_become_the_emotion(self):
        f = EmotionFilter(stable_frames=1, min_confidence=25)
        self.assertEqual(f.update(self.scores(neutral=65, fear=35), 0), 'neutral')


if __name__ == '__main__':
    unittest.main()
