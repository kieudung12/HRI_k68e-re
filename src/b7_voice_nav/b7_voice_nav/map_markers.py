"""RViz semantic markers: optional region colours, labels and destinations."""
import math
from pathlib import Path

import cv2
import numpy as np
import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from visualization_msgs.msg import Marker, MarkerArray

from .common import load_regions, normalize, world_to_pixel
from .segment import grow_regions


PALETTE = [(0.16, 0.43, 0.82), (0.85, 0.51, 0.12), (0.05, 0.58, 0.48)]


def make_markers(map_path, regions):
    """Use the same free-cell segmentation as segment_map; never colour walls."""
    with open(map_path, encoding='utf-8') as stream:
        meta = yaml.safe_load(stream)
    image = cv2.imread(str(map_path.parent / meta['image']), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f'Không đọc được ảnh bản đồ: {map_path}')
    probability = image.astype(np.float32) / 255
    if not meta.get('negate', 0):
        probability = 1 - probability
    free = probability < meta['free_thresh']
    height = image.shape[0]
    labels = grow_regions(free, [world_to_pixel(r['goal']['x'], r['goal']['y'], meta, height)
                                for r in regions])
    result = MarkerArray()

    def add(namespace, kind, colour, frame='map'):
        marker = Marker()
        marker.header.frame_id = frame
        marker.ns = namespace
        marker.id = len(result.markers)
        marker.type = kind
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.color.r, marker.color.g, marker.color.b = colour
        marker.color.a = 1.0
        result.markers.append(marker)
        return marker

    resolution = meta['resolution']
    ox, oy, yaw = meta['origin']
    for index, region in enumerate(regions):
        colour = PALETTE[index % len(PALETTE)]
        floor = add('region_floors', Marker.TRIANGLE_LIST, colour)
        floor.scale.x = floor.scale.y = floor.scale.z = 1.0
        floor.color.a = 0.16
        # Local coordinates keep cell orientation correct for rotated map origins.
        floor.pose.position.x, floor.pose.position.y = ox, oy
        floor.pose.orientation.z, floor.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        # Merge each row's contiguous cells into flat rectangles (two triangles).
        # This avoids thousands of overlapping translucent cube edges in RViz.
        for y, row in enumerate(labels):
            edges = np.flatnonzero(np.diff(np.r_[False, row == index, False]))
            for start, end in edges.reshape(-1, 2):
                x0, x1 = float(start) * resolution, float(end) * resolution
                y0, y1 = (height - y - 1) * resolution, (height - y) * resolution
                floor.points.extend(Point(x=x, y=py, z=0.015) for x, py in
                                    [(x0, y0), (x1, y0), (x1, y1),
                                     (x0, y0), (x1, y1), (x0, y1)])

        gx, gy = float(region['goal']['x']), float(region['goal']['y'])
        ring = add('destinations', Marker.LINE_STRIP, colour)
        ring.scale.x = 0.02
        ring.points = [Point(x=gx + 0.16 * math.cos(t), y=gy + 0.16 * math.sin(t), z=0.06)
                       for t in np.linspace(0, 2 * math.pi, 49)]
        dot = add('destinations', Marker.CYLINDER, colour)
        dot.pose.position = Point(x=gx, y=gy, z=0.06)
        dot.scale.x = dot.scale.y = 0.07
        dot.scale.z = 0.02

        label = add('region_labels', Marker.TEXT_VIEW_FACING, colour)
        label.pose.position = Point(x=gx, y=gy + 0.80, z=0.12)
        label.scale.z = 0.34
        label.text = str(region['id'])
        name = add('region_labels', Marker.TEXT_VIEW_FACING, (0.20, 0.26, 0.34))
        name.pose.position = Point(x=gx, y=gy + 0.48, z=0.12)
        name.scale.z = 0.16
        # RViz's bundled font renders ASCII consistently on Ubuntu/OGRE.
        name.text = normalize(region['name']).upper().replace(' ', '-')

    return result


class MapMarkers(Node):
    def __init__(self):
        super().__init__('map_markers')
        share = Path(get_package_share_directory('b7_voice_nav'))
        self.declare_parameter('map_file', str(share / 'maps/map.yaml'))
        self.declare_parameter('regions_file', str(share / 'config/regions.yaml'))
        markers = make_markers(Path(self.get_parameter('map_file').value),
                               load_regions(self.get_parameter('regions_file').value))
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(MarkerArray, '/b7/map_markers', qos)
        self.publisher.publish(markers)
        self.get_logger().info('RViz: đã hiển thị nhãn vùng và điểm đích')


def main():
    rclpy.init()
    node = MapMarkers()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
