#!/usr/bin/env python3
"""Generate the B7 world and a ground-truth occupancy map from the same boxes."""
from pathlib import Path
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[1] / 'src/b7_voice_nav'
# name, center x/y, box width/length, height. Doors are gaps in wall boxes.
BOXES = [
    ('west', -5, 0, .15, 8, 1.8), ('east', 5, 0, .15, 8, 1.8),
    ('north', 0, 4, 10.15, .15, 1.8), ('south', 0, -4, 10.15, .15, 1.8),
    ('north_left', -4.4, 1, 1.2, .15, 1.8),
    ('north_mid', 0, 1, 5.2, .15, 1.8),
    ('north_right', 4.4, 1, 1.2, .15, 1.8),
    ('room_divider', 0, 2.5, .15, 3, 1.8),
    ('south_left', -3.1, -1, 3.8, .15, 1.8),
    ('south_right', 3.1, -1, 3.8, .15, 1.8),
    ('obstacle_a', -4.1, 3.25, .45, .45, .7),
    ('obstacle_b', 4.1, 3.25, .45, .45, .7),
    ('obstacle_c', 3.7, -3.1, .55, .55, .7),
]

def main():
    sdf = ['''<?xml version="1.0"?>
<sdf version="1.6"><world name="b7_campus">
<physics name="step" type="ignored"><max_step_size>0.003</max_step_size><real_time_factor>1</real_time_factor></physics>
<plugin filename="ignition-gazebo-physics-system" name="ignition::gazebo::systems::Physics"/>
<plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
<plugin filename="ignition-gazebo-scene-broadcaster-system" name="ignition::gazebo::systems::SceneBroadcaster"/>
<scene><ambient>0.75 0.75 0.75 1</ambient><background>0.8 0.85 0.9 1</background><shadows>true</shadows></scene>
<light name="sun" type="directional"><pose>0 0 8 0 0 0</pose><direction>-0.5 0.1 -0.9</direction><diffuse>0.8 0.8 0.8 1</diffuse></light>
<model name="floor"><static>true</static><link name="link"><collision name="collision"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></collision><visual name="visual"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry><material><ambient>0.82 0.82 0.82 1</ambient><diffuse>0.82 0.82 0.82 1</diffuse></material></visual></link></model>''']
    for name, x, y, sx, sy, height in BOXES:
        size = f'{sx} {sy} {height}'
        sdf.append(f'''<model name="{name}"><static>true</static><pose>{x} {y} {height/2} 0 0 0</pose><link name="link"><collision name="collision"><geometry><box><size>{size}</size></box></geometry></collision><visual name="visual"><geometry><box><size>{size}</size></box></geometry><material><ambient>0.38 0.45 0.50 1</ambient><diffuse>0.38 0.45 0.50 1</diffuse></material></visual></link></model>''')
    sdf.append('</world></sdf>\n')
    (ROOT / 'worlds/b7_campus.sdf').write_text('\n'.join(sdf))
    # 0.05m grid, occupancy at pixel centers; outside enclosure is unknown.
    resolution, origin_x, origin_y = .05, -5.5, -4.5
    width, height = 220, 180
    xs = origin_x + (np.arange(width) + .5) * resolution
    ys = origin_y + (np.arange(height)[::-1] + .5) * resolution
    xx, yy = np.meshgrid(xs, ys)
    image = np.full((height, width), 205, np.uint8)
    image[(abs(xx) < 5) & (abs(yy) < 4)] = 254
    for _, x, y, sx, sy, _ in BOXES:
        image[(abs(xx-x) <= sx/2) & (abs(yy-y) <= sy/2)] = 0
    if not cv2.imwrite(str(ROOT / 'maps/map.pgm'), image):
        raise RuntimeError('Could not write map')
    (ROOT / 'maps/map.yaml').write_text('image: map.pgm\nmode: trinary\nresolution: 0.05\norigin: [-5.5, -4.5, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')

if __name__ == '__main__':
    main()
