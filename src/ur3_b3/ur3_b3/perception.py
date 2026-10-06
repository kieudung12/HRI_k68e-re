"""Fixed overhead camera: HSV cube detection and a simple pinhole table map."""

import json
import time

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String


# Camera mount, cube height, and zone markers come from worlds/table.sdf.
# Object positions deliberately come only from the image.
CAMERA_X, CAMERA_Y, CAMERA_Z = 0.38, 0.0, 1.15
CUBE_TOP_Z = 0.335
ZONES = {'zone_a': (0.30, -0.16), 'zone_b': (0.30, 0.0),
         'zone_c': (0.30, 0.16)}
ZONE_LABELS = {'zone_a': 'A', 'zone_b': 'B', 'zone_c': 'C'}
ZONE_HALF_SIZE = 0.05
HUE_RANGES = {
    'red_cube': [(0, 10), (170, 179)],
    'yellow_cube': [(20, 38)],
    'blue_cube': [(100, 130)],
    'green_cube': [(45, 82)],
    'purple_cube': [(132, 165)],
}
DRAW_COLORS = {
    'red_cube': (0, 0, 255), 'yellow_cube': (0, 220, 255),
    'blue_cube': (255, 0, 0), 'green_cube': (0, 180, 0),
    'purple_cube': (200, 0, 200),
}
ZONE_COLORS = {'zone_a': (255, 160, 0), 'zone_b': (0, 180, 255),
               'zone_c': (180, 80, 220)}
PANEL_WIDTH = 280


def world_to_pixel(x, y, camera_info):
    """Project a table point using the same fixed-height pinhole model."""
    fx, fy = camera_info.k[0], camera_info.k[4]
    cx, cy = camera_info.k[2], camera_info.k[5]
    depth = CAMERA_Z - CUBE_TOP_Z
    return int(round(cx - (y - CAMERA_Y) * fx / depth)), int(round(
        cy - (x - CAMERA_X) * fy / depth))


def draw_zones(image, camera_info, zones):
    for zone, (zx, zy) in ZONES.items():
        corners = [world_to_pixel(zx + dx, zy + dy, camera_info)
                   for dx, dy in ((-ZONE_HALF_SIZE, -ZONE_HALF_SIZE),
                                  (-ZONE_HALF_SIZE, ZONE_HALF_SIZE),
                                  (ZONE_HALF_SIZE, ZONE_HALF_SIZE),
                                  (ZONE_HALF_SIZE, -ZONE_HALF_SIZE))]
        polygon = cv2.convexHull(np.array(corners, dtype='int32'))
        color = ZONE_COLORS[zone]
        cv2.polylines(image, [polygon], True, color, 2)
        cx, cy = world_to_pixel(zx, zy, camera_info)
        label = ZONE_LABELS[zone]
        cv2.putText(image, label, (max(0, cx - 8), max(18, cy - 25)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2, cv2.LINE_AA)


def draw_panel(image, camera_width, state):
    """Draw a stable legend so labels do not collide over nearby cubes."""
    left = camera_width
    cv2.rectangle(image, (left, 0), (image.shape[1], image.shape[0]),
                  (28, 34, 43), -1)

    def text(value, x, y, color=(235, 240, 245), scale=0.46, thickness=1):
        cv2.putText(image, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, thickness, cv2.LINE_AA)

    text('PERCEPTION DEBUG', left + 16, 30, (255, 255, 255), 0.62, 2)
    text('LIVE  |  RGB + HSV', left + 16, 55, (120, 220, 180), 0.42, 1)
    text('INPUT', left + 16, 90, (150, 165, 180), 0.38, 1)
    text('/camera', left + 82, 90, (235, 240, 245), 0.42, 1)

    text('OBJECTS', left + 16, 128, (150, 165, 180), 0.38, 1)
    y = 155
    for name, item in state['objects'].items():
        color = DRAW_COLORS[name]
        cv2.rectangle(image, (left + 16, y - 11), (left + 28, y + 1), color, -1)
        location = item['location'] if item['detected'] else 'NOT DETECTED'
        text(name, left + 38, y, (235, 240, 245), 0.39, 1)
        text(location, left + 38, y + 16,
             (120, 220, 180) if item['detected'] else (100, 130, 150),
             0.36, 1)
        y += 45

    text('ZONES', left + 16, y + 8, (150, 165, 180), 0.38, 1)
    y += 35
    for zone in ZONES:
        occupant = state['zones'][zone]
        label = f'{ZONE_LABELS[zone]}  {"EMPTY" if occupant is None else occupant}'
        color = ZONE_COLORS[zone]
        cv2.rectangle(image, (left + 16, y - 12), (left + 28, y), color, 2)
        text(label, left + 40, y, (235, 240, 245), 0.40, 1)
        y += 30

    y += 12
    status = 'COMPLETE' if state['complete'] else 'INCOMPLETE'
    text('STATUS', left + 16, y, (150, 165, 180), 0.38, 1)
    text(status, left + 16, y + 25,
         (100, 230, 160) if state['complete'] else (80, 150, 255), 0.52, 2)
    if state['errors']:
        text('ERROR', left + 16, y + 58, (80, 150, 255), 0.38, 1)
        text(str(state['errors'][0])[:31], left + 16, y + 80,
             (80, 150, 255), 0.34, 1)


def detect_objects(bgr, camera_info):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    fx, fy = camera_info.k[0], camera_info.k[4]
    cx, cy = camera_info.k[2], camera_info.k[5]
    depth = CAMERA_Z - CUBE_TOP_Z
    objects = {}
    zones = {name: None for name in ZONES}
    errors = []
    camera_height, camera_width = bgr.shape[:2]
    debug = np.zeros((camera_height, camera_width + PANEL_WIDTH, 3), dtype=np.uint8)
    debug[:, :camera_width] = bgr
    for name, ranges in HUE_RANGES.items():
        objects[name] = {'detected': False, 'location': 'not_detected',
                         'pixel': None}
        mask = None
        for low, high in ranges:
            part = cv2.inRange(hsv, (low, 90, 60), (high, 255, 255))
            mask = part if mask is None else cv2.bitwise_or(mask, part)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        valid = [contour for contour in contours if cv2.contourArea(contour) >= 150]
        if not valid:
            continue
        if len(valid) > 1:
            errors.append(f'{name} has multiple detected regions')
        contour = max(valid, key=cv2.contourArea)
        moments = cv2.moments(contour)
        if moments['m00'] == 0:
            continue
        u = moments['m10'] / moments['m00']
        v = moments['m01'] / moments['m00']
        x = CAMERA_X + (cy - v) * depth / fy
        y = CAMERA_Y + (cx - u) * depth / fx
        if not (0.15 <= x <= 0.75 and -0.36 <= y <= 0.36):
            continue
        location = 'table'
        for zone, (zx, zy) in ZONES.items():
            if abs(x - zx) <= ZONE_HALF_SIZE and abs(y - zy) <= ZONE_HALF_SIZE:
                location = zone
                if zones[zone] is not None:
                    errors.append(f'{zone} contains multiple detected cubes')
                    zones[zone] = 'INVALID:MULTIPLE_OBJECTS'
                else:
                    zones[zone] = name
                break
        if len(valid) > 1 and location in ZONES:
            zones[location] = 'INVALID:MULTIPLE_OBJECTS'
        objects[name] = {'detected': True, 'location': location,
                         'pixel': [int(round(u)), int(round(v))],
                         'x': round(x, 3), 'y': round(y, 3)}
        color = DRAW_COLORS[name]
        x0, y0, width, height = cv2.boundingRect(contour)
        cv2.drawContours(debug, [contour], -1, color, 2)
        cv2.rectangle(debug, (x0, y0), (x0 + width, y0 + height), color, 1)
        cv2.circle(debug, (int(round(u)), int(round(v))), 4, color, -1)
        short_name = name.replace('_cube', '')
        cv2.putText(debug, short_name, (x0, max(18, y0 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
    missing = [name for name, item in objects.items() if not item['detected']]
    state = {'source': 'camera_rgb_hsv', 'camera_topic': '/camera',
             'objects': objects, 'zones': zones, 'missing': sorted(missing),
             'complete': not missing and not errors, 'errors': errors}
    draw_zones(debug, camera_info, zones)
    cv2.rectangle(debug, (0, 0), (camera_width, 42), (25, 30, 38), -1)
    cv2.putText(debug, 'CAMERA VIEW  |  RGB + HSV', (14, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (245, 248, 250), 2, cv2.LINE_AA)
    draw_panel(debug, camera_width, state)
    return state, debug


class Perception(Node):
    def __init__(self):
        super().__init__('perception')
        self.bridge = CvBridge()
        self.camera_info = None
        self.last_publish = 0.0
        self.last_signature = None
        self.last_state = None
        self.publisher = self.create_publisher(String, '/environment_state', 10)
        self.debug_publisher = self.create_publisher(
            Image, '/perception/debug_image', qos_profile_sensor_data)
        self.create_subscription(CameraInfo, '/camera_info', self.on_camera_info,
                                 qos_profile_sensor_data)
        self.create_subscription(Image, '/camera', self.on_image,
                                 qos_profile_sensor_data)

    def on_camera_info(self, msg):
        self.camera_info = msg

    def on_image(self, msg):
        if self.camera_info is None or time.monotonic() - self.last_publish < 0.4:
            return
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            state, debug = detect_objects(bgr, self.camera_info)
        except Exception as exc:
            self.get_logger().error(f'Image processing failed: {exc}')
            return
        debug_msg = self.bridge.cv2_to_imgmsg(debug, encoding='bgr8')
        debug_msg.header = msg.header
        self.debug_publisher.publish(debug_msg)
        output = String()
        output.data = json.dumps(state, sort_keys=True)
        self.publisher.publish(output)
        signature = json.dumps({
            'objects': {name: item['location']
                        for name, item in state['objects'].items()},
            'zones': state['zones'], 'complete': state['complete'],
            'errors': state['errors'], 'missing': state['missing']}, sort_keys=True)
        if signature != self.last_signature:
            previous = self.last_state or {'objects': {}, 'zones': {}}
            for name, item in state['objects'].items():
                old = previous['objects'].get(name, {}).get('location')
                if old != item['location']:
                    self.get_logger().info(f'{name} -> {item["location"]}')
            for zone, occupant in state['zones'].items():
                old = previous['zones'].get(zone)
                if old != occupant:
                    shown = 'EMPTY' if occupant is None else occupant
                    self.get_logger().info(f'{zone} -> {shown}')
            self.last_signature = signature
            self.last_state = state
        self.last_publish = time.monotonic()


def main():
    rclpy.init()
    node = Perception()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
