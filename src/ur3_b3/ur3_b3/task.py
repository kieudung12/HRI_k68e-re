"""Run a camera-guided pick and place without an LLM."""

import argparse
import json

import rclpy

from .perception import HUE_RANGES, ZONES
from .planner import execute_plan, request_plan, validate_plan
from .skills import RobotSkills


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--object', choices=HUE_RANGES)
    parser.add_argument('--target', choices=ZONES)
    parser.add_argument('--command', help='Natural-language command for the LLM')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print the validated LLM plan without moving')
    args = parser.parse_args()
    if bool(args.command) == bool(args.object and args.target):
        parser.error('Give --command, or both --object and --target')

    rclpy.init()
    robot = None
    try:
        robot = RobotSkills()
        state = robot.state()
        if args.command:
            document = request_plan(args.command, state)
            steps = validate_plan(document, state)
            print(json.dumps({'plan': steps}, indent=2), flush=True)
            if not args.dry_run:
                execute_plan(robot, steps)
        elif state['zones'][args.target] != args.object:
            robot.clear_zone(args.target)
            robot.pick(args.object)
            robot.place(args.object, args.target)
        if not args.command:
            robot.home()
    finally:
        if robot is not None:
            robot.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
