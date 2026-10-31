"""Grow labelled regions through free occupancy cells, respecting walls."""
import argparse
import os
from collections import deque

import cv2
import numpy as np
import yaml
from .common import load_regions, world_to_pixel


def grow_regions(free, seeds):
    """Multi-source BFS: each cell belongs to the nearest seed along free cells."""
    height, width = free.shape
    labels = np.full(free.shape, -1, dtype=np.int32)
    pending = deque()
    for index, (x, y) in enumerate(seeds):
        if not (0 <= x < width and 0 <= y < height) or not free[y, x]:
            raise ValueError('Điểm mẫu phải nằm ở ô trống trong bản đồ')
        if labels[y, x] >= 0:
            raise ValueError('Hai vùng không được dùng chung một ô điểm mẫu')
        labels[y, x] = index
        pending.append((x, y))
    while pending:
        x, y = pending.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (0 <= nx < width and 0 <= ny < height and
                    free[ny, nx] and labels[ny, nx] < 0):
                labels[ny, nx] = labels[y, x]
                pending.append((nx, ny))
    return labels


def main():
    from ament_index_python.packages import get_package_share_directory
    share = get_package_share_directory('b7_voice_nav')
    p = argparse.ArgumentParser(description='Vẽ phân vùng bản đồ')
    p.add_argument('--map', default=os.path.join(share, 'maps/map.yaml'))
    p.add_argument('--regions', default=os.path.join(share, 'config/regions.yaml'))
    p.add_argument('--output', default='regions.png')
    p.add_argument('--min-clearance', type=float, default=0.22,
                   help='Khoảng cách tối thiểu từ goal tới ô không trống, mét')
    args = p.parse_args()
    with open(args.map, encoding='utf-8') as f:
        meta = yaml.safe_load(f)
    img = cv2.imread(os.path.join(os.path.dirname(args.map), meta['image']), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit('Không đọc được ảnh bản đồ')
    occupied_probability = img.astype(np.float32) / 255 if meta.get('negate', 0) else (255 - img.astype(np.float32)) / 255
    free = (occupied_probability < meta['free_thresh']).astype(np.uint8)
    regions = load_regions(args.regions)
    h, w = img.shape
    seeds = [world_to_pixel(r['goal']['x'], r['goal']['y'], meta, h) for r in regions]
    count, components = cv2.connectedComponents(free, connectivity=8)
    del count
    labels = []
    clearance = cv2.distanceTransform(free, cv2.DIST_L2, 5) * meta['resolution']
    for r, (x, y) in zip(regions, seeds):
        if not (0 <= x < w and 0 <= y < h) or not free[y, x]:
            raise SystemExit(f"Điểm đích {r['id']} nằm ngoài bản đồ hoặc không ở ô trống")
        if clearance[y, x] < args.min_clearance:
            raise SystemExit(f"Điểm đích {r['id']} quá gần vật cản: {clearance[y, x]:.2f} m")
        labels.append(components[y, x])
    if len(set(labels)) != 1:
        raise SystemExit('Các điểm đích không cùng vùng trống liên thông')
    region_labels = grow_regions(free, seeds)
    palette = [(80, 170, 245), (110, 210, 120), (230, 150, 110), (180, 110, 220), (100, 210, 210)]
    result = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for i, r in enumerate(regions):
        result[region_labels == i] = palette[i % len(palette)]
        x, y = seeds[i]
        cv2.circle(result, (x, y), 3, (0, 0, 0), -1)
        cv2.putText(result, r['id'], (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)
        print(f"Vùng {r['id']}: {np.count_nonzero(region_labels == i)} ô; "
              f"goal cách vật cản {clearance[y, x]:.2f} m")
    if not cv2.imwrite(args.output, result):
        raise SystemExit('Không ghi được ảnh đầu ra')
    print(f'Đã lưu {args.output}; các chấm là điểm đích map-frame: {seeds}')

if __name__ == '__main__':
    main()
