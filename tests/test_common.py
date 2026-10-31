import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src/b7_voice_nav'))
from b7_voice_nav.common import load_regions, parse_command, world_to_pixel

REGIONS = load_regions(os.path.join(os.path.dirname(__file__), '../src/b7_voice_nav/config/regions.yaml'))

class TestCommands(unittest.TestCase):
    def test_routes(self):
        for command, expected in [
            ('Đi đến khu vực A.', ['A']),
            ('Di chuyển từ khu vực A đến khu vực B.', ['A', 'B']),
            ('Đi đến phòng thí nghiệm.', ['C']),
            ('Đi đến khu vực bê.', ['B']),
            ('Đi tới khu vực xê nhé.', ['C']),
            ('Hãy đi đến phòng học.', ['A']),
            ('Đi vùng A', ['A']),
            ('Đi từ phòng A qua khu vực C rồi đến phòng B', ['A', 'C', 'B']),
        ]:
            with self.subTest(command=command):
                self.assertEqual([r['id'] for r in parse_command(command, REGIONS)], expected)

    def test_unknown_rejects_whole_route(self):
        for command in ['Đi đến khu vực D', 'Đi từ khu vực A đến khu vực D', 'bật đèn', 'đi đến', 'Đi từ A đến', 'Đi đến khu vực đê', 'Đi đến khu vực 100']:
            with self.subTest(command=command), self.assertRaises(ValueError):
                parse_command(command, REGIONS)

    def test_natural_route_connectors(self):
        for command, expected in [
            ('Đi đến khu vực A rồi sang khu vực B rồi sang khu vực C', ['A', 'B', 'C']),
            ('Đi khu A rồi sang khu B rồi sang khu C', ['A', 'B', 'C']),
            ('Di chuyển từ khu A sang khu B', ['A', 'B']),
            ('Đi từ khu A qua phòng thí nghiệm rồi sang khu B', ['A', 'C', 'B']),
            ('Đi đến khu bê sau đó sang khu xê', ['B', 'C']),
        ]:
            with self.subTest(command=command):
                self.assertEqual([r['id'] for r in parse_command(command, REGIONS)], expected)

    def test_short_region_name(self):
        self.assertEqual([r['id'] for r in parse_command('Đi đến khu A', REGIONS)], ['A'])

    def test_polite_endings_do_not_create_destinations(self):
        for command, expected in [
            ('Di chuyển đến khu vực A cho tôi.', ['A']),
            ('Đi tới khu vực B cho tôi nhé.', ['B']),
            ('Hãy đi đến phòng thí nghiệm giúp tôi với.', ['C']),
            ('Đi đến khu A giúp mình nha.', ['A']),
            ('Đi từ khu A tới khu B cho tôi.', ['A', 'B']),
            ('Đi khu A rồi sang khu B rồi sang khu C giúp em với ạ.', ['A', 'B', 'C']),
        ]:
            with self.subTest(command=command):
                self.assertEqual([r['id'] for r in parse_command(command, REGIONS)], expected)

    def test_polite_endings_still_reject_invalid_routes(self):
        for command in ['Đi đến khu D cho tôi', 'Đi từ khu A đến khu D giúp tôi với',
                        'Đi đến cho tôi', 'Đi khu A rồi sang giúp tôi',
                        'Đi đến khu A và khu D cho tôi']:
            with self.subTest(command=command), self.assertRaises(ValueError):
                parse_command(command, REGIONS)

    def test_invalid_natural_route_is_rejected_entirely(self):
        for command in ['Đi khu A rồi sang khu D', 'Đi đến khu A rồi sang',
                        'Đi đến đến khu A', 'Đi khu vực 100 rồi sang khu B']:
            with self.subTest(command=command), self.assertRaises(ValueError):
                parse_command(command, REGIONS)

    def test_map_conversion(self):
        meta = {'origin': [-5.5, -4.5, 0], 'resolution': 0.05}
        self.assertEqual(world_to_pixel(-3.2, 2.4, meta, 180), (46, 41))
        self.assertEqual(world_to_pixel(0, 1, {'origin': [0, 0, 1.5707963267948966], 'resolution': 1}, 10), (1, 9))

if __name__ == '__main__':
    unittest.main()
