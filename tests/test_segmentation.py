from collections import deque
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/b7_voice_nav'))
from b7_voice_nav.common import load_regions, world_to_pixel
from b7_voice_nav.segment import grow_regions


class TestSegmentation(unittest.TestCase):
    def test_wall_blocks_assignment_and_disconnected_space_stays_unlabelled(self):
        free = np.ones((5, 9), dtype=np.uint8)
        free[:, 4] = 0
        free[0, 1] = free[1, 0] = 0  # isolate the free cell (0, 0)
        labels = grow_regions(free, [(2, 2), (6, 2)])
        self.assertTrue(np.all(labels[:, 4] == -1))
        self.assertTrue(np.all(labels[1:, 1:4][free[1:, 1:4] != 0] == 0))
        self.assertTrue(np.all(labels[:, 5:] == 1))
        self.assertEqual(labels[0, 0], -1)

    def test_actual_map_has_three_connected_regions_and_safe_goals(self):
        map_dir = ROOT / 'src/b7_voice_nav/maps'
        meta = yaml.safe_load((map_dir / 'map.yaml').read_text())
        image = cv2.imread(str(map_dir / meta['image']), cv2.IMREAD_GRAYSCALE)
        probability = (255 - image.astype(float)) / 255
        free = (probability < meta['free_thresh']).astype(np.uint8)
        regions = load_regions(ROOT / 'src/b7_voice_nav/config/regions.yaml')
        seeds = [world_to_pixel(r['goal']['x'], r['goal']['y'], meta, len(image))
                 for r in regions]
        labels = grow_regions(free, seeds)
        clearance = cv2.distanceTransform(free, cv2.DIST_L2, 5) * meta['resolution']
        self.assertEqual(set(np.unique(labels[labels >= 0])), {0, 1, 2})
        self.assertTrue(np.all(labels[free == 0] == -1))
        for i, (x, y) in enumerate(seeds):
            with self.subTest(region=regions[i]['id']):
                self.assertEqual(labels[y, x], i)
                self.assertGreaterEqual(clearance[y, x], 0.22)
                seen, queue = {(x, y)}, deque([(x, y)])
                while queue:
                    px, py = queue.popleft()
                    for nx, ny in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                        if (0 <= nx < labels.shape[1] and 0 <= ny < labels.shape[0]
                                and labels[ny, nx] == i and (nx, ny) not in seen):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
                self.assertEqual(len(seen), np.count_nonzero(labels == i))

    def test_invalid_seeds(self):
        free = np.ones((3, 3), dtype=np.uint8)
        free[0, 0] = 0
        for seeds in [[(0, 0)], [(4, 2)], [(1, 1), (1, 1)]]:
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                grow_regions(free, seeds)


if __name__ == '__main__':
    unittest.main()
