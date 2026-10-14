#!/usr/bin/env python3
"""Small terminal teleop for the LEC4 simulation: W/S drive, A/D turn."""
import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist


def main():
    if not sys.stdin.isatty():
        raise SystemExit('Mo teleop trong terminal de nhan phim WASD.')

    rclpy.init()
    node = rclpy.create_node('lec4_wasd_teleop')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)
    old_settings = termios.tcgetattr(sys.stdin)
    speed, turn, keep_for = 0.28, 0.80, 0.60
    last_key = ''
    active_until = 0.0
    print('\nW/S: tien/lui | A/D: quay | Space: dung | Q: thoat\n', flush=True)
    print(f'Toc do: {speed:.2f} m/s | Quay: {turn:.2f} rad/s. Giu phim de di lien tuc.\n',
          flush=True)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                last_key = sys.stdin.read(1).lower()
                active_until = time.monotonic() + keep_for
                if last_key == 'q':
                    break
            msg = Twist()
            if time.monotonic() < active_until:
                if last_key == 'w':
                    msg.linear.x = speed
                elif last_key == 's':
                    msg.linear.x = -speed
                elif last_key == 'a':
                    msg.angular.z = turn
                elif last_key == 'd':
                    msg.angular.z = -turn
            pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=0)
    except KeyboardInterrupt:
        pass
    finally:
        pub.publish(Twist())
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.destroy_node()
        rclpy.shutdown()
        print('Da gui lenh dung.')


if __name__ == '__main__':
    main()
