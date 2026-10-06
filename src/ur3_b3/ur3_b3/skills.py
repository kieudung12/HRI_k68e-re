"""Small MoveIt and ros2_control skills for the physical UR3e sorting scene."""

import json
import math
import time
from pathlib import Path

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Pose, PoseStamped
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import CollisionObject, Constraints, JointConstraint
from moveit_msgs.srv import (ApplyPlanningScene, GetCartesianPath,
                             GetMotionPlan, GetPositionIK)
import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectoryPoint

from .perception import ZONES


ARM = ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
       'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint')
GRIPPER = ('robotiq_85_left_knuckle_joint', 'robotiq_85_right_knuckle_joint',
           'robotiq_85_left_inner_knuckle_joint', 'robotiq_85_right_inner_knuckle_joint',
           'robotiq_85_left_finger_tip_joint', 'robotiq_85_right_finger_tip_joint')
PICK_Z = 0.475
HOVER_Z = 0.55
HOME = dict(zip(ARM, (0.0, -1.5707, 0.0, -1.5707, 0.0, 0.0)))


def _load_motion_config():
    """Read arm speed limits from the package controller YAML."""
    defaults = {
        'velocity_scaling': 0.05,
        'acceleration_scaling': 0.05,
        'gripper_motion_time': 3.0,
        'gripper_close_position': 0.52,
    }
    try:
        path = Path(get_package_share_directory('ur3_b3')) / 'config' / 'controllers.yaml'
        document = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        values = document.get('robot_skills', {}).get('ros__parameters', {})
        defaults.update({name: float(values[name]) for name in defaults if name in values})
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        pass
    defaults['velocity_scaling'] = min(max(defaults['velocity_scaling'], 0.001), 1.0)
    defaults['acceleration_scaling'] = min(max(defaults['acceleration_scaling'], 0.001), 1.0)
    defaults['gripper_motion_time'] = min(max(defaults['gripper_motion_time'], 0.5), 15.0)
    defaults['gripper_close_position'] = min(max(defaults['gripper_close_position'], 0.1), 0.75)
    return defaults

# Temporary table cells are ordered from the robot's comfortable working area
# outwards.  The list is deliberately larger than the five initial cubes so a
# sequence can move several cubes without reusing a cell.  A cell is accepted
# only when it is clear in the camera state *and* MoveIt can plan to it.
STAGING_POSITIONS = (
    (0.34, -0.25), (0.44, -0.25),
    (0.34, 0.25), (0.44, 0.25),
    (0.30, -0.34), (0.30, 0.34), (0.34, -0.34), (0.34, 0.34),
    (0.40, -0.34), (0.40, 0.34),
    (0.50, -0.25), (0.50, 0.25),
)


class RobotSkills(Node):
    def __init__(self):
        super().__init__('robot_skills')
        motion = _load_motion_config()
        self.velocity_scaling = motion['velocity_scaling']
        self.acceleration_scaling = motion['acceleration_scaling']
        self.gripper_motion_time = motion['gripper_motion_time']
        self.gripper_close_position = motion['gripper_close_position']
        self.get_logger().info(
            f'motion speed: velocity={self.velocity_scaling:.3f} '
            f'acceleration={self.acceleration_scaling:.3f} '
            f'gripper={self.gripper_motion_time:.1f}s '
            f'close={self.gripper_close_position:.2f}')
        self.environment = None
        self.environment_time = 0.0
        self.joints = None
        self.held = None
        self.create_subscription(String, '/environment_state', self._on_environment, 10)
        self.create_subscription(JointState, '/joint_states', self._on_joints, 10)
        self.ik = self.create_client(GetPositionIK, '/compute_ik')
        self.cartesian = self.create_client(GetCartesianPath, '/compute_cartesian_path')
        self.planner = self.create_client(GetMotionPlan, '/plan_kinematic_path')
        self.scene = self.create_client(ApplyPlanningScene, '/apply_planning_scene')
        self.arm_action = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self.gripper_action = ActionClient(
            self, FollowJointTrajectory, '/gripper_controller/follow_joint_trajectory')
        for client in (self.ik, self.cartesian, self.planner, self.scene):
            if not client.wait_for_service(timeout_sec=15):
                raise RuntimeError(f'MoveIt service unavailable: {client.srv_name}')
        for client in (self.arm_action, self.gripper_action):
            if not client.wait_for_server(timeout_sec=15):
                raise RuntimeError('Robot action server unavailable')

    def _on_environment(self, msg):
        self.environment = json.loads(msg.data)
        self.environment_time = time.monotonic()

    def _on_joints(self, msg):
        self.joints = dict(zip(msg.name, msg.position))

    def _wait(self, future, seconds=90):
        rclpy.spin_until_future_complete(self, future, timeout_sec=seconds)
        if not future.done():
            raise RuntimeError('ROS request timed out')
        result = future.result()
        if result is None:
            raise RuntimeError('ROS request returned no result')
        return result

    def state(self, after=0.0, timeout=10):
        deadline = time.monotonic() + timeout
        while (self.environment is None or self.environment_time <= after
               or not self.environment['complete']):
            if time.monotonic() > deadline:
                raise RuntimeError('Camera state is missing or incomplete')
            rclpy.spin_once(self, timeout_sec=0.2)
        return self.environment

    def _pose(self, x, y, z):
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = x, y, z
        pose.orientation.x = 1.0  # gripper points straight down
        pose.orientation.w = 0.0
        return pose

    def _table(self, add):
        request = ApplyPlanningScene.Request()
        request.scene.is_diff = True
        obj = CollisionObject()
        obj.id = 'table'
        obj.header.frame_id = 'world'
        obj.operation = CollisionObject.ADD if add else CollisionObject.REMOVE
        if add:
            box = SolidPrimitive()
            box.type = SolidPrimitive.BOX
            box.dimensions = [0.60, 0.72, 0.03]
            obj.primitives = [box]
            pose = Pose()
            pose.position.x, pose.position.z = 0.45, 0.285
            pose.orientation.w = 1.0
            obj.primitive_poses = [pose]
        request.scene.world.collision_objects = [obj]
        if not self._wait(self.scene.call_async(request)).success:
            raise RuntimeError('Could not update MoveIt table collision')

    def _cartesian(self, x, y, z, start=None):
        request = GetCartesianPath.Request()
        request.header.frame_id = 'world'
        if start is None:
            request.start_state.is_diff = True
        else:
            request.start_state = start
        request.group_name = 'ur_manipulator'
        request.link_name = 'tool0'
        request.waypoints = [self._pose(x, y, z)]
        request.max_step = 0.005
        request.jump_threshold = 0.0
        request.avoid_collisions = False
        request.max_velocity_scaling_factor = self.velocity_scaling
        request.max_acceleration_scaling_factor = self.acceleration_scaling
        response = self._wait(self.cartesian.call_async(request), 25)
        trajectory = response.solution.joint_trajectory
        spans = []
        for index in range(len(trajectory.joint_names)):
            values = [point.positions[index] for point in trajectory.points]
            spans.append(max(values) - min(values) if values else 0.0)
        if (response.error_code.val != 1 or response.fraction < 0.99
                or max(spans, default=0.0) > 1.2):
            raise RuntimeError('No short Cartesian path to the requested pose')
        return response.solution

    def _plan_joints(self, target):
        while self.joints is None:
            rclpy.spin_once(self, timeout_sec=0.2)
        target = dict(target)
        for name, value in target.items():
            equivalents = [value + 2 * math.pi * turns for turns in range(-2, 3)
                           if abs(value + 2 * math.pi * turns) <= 2 * math.pi]
            if not equivalents:
                raise RuntimeError(f'{name} goal is outside joint limits')
            target[name] = min(equivalents,
                               key=lambda angle: abs(angle - self.joints[name]))
        request = GetMotionPlan.Request()
        plan = request.motion_plan_request
        plan.group_name = 'ur_manipulator'
        plan.start_state.is_diff = True
        plan.num_planning_attempts = 20
        plan.allowed_planning_time = 10.0
        plan.max_velocity_scaling_factor = self.velocity_scaling
        plan.max_acceleration_scaling_factor = self.acceleration_scaling
        goal = Constraints()
        for name, value in target.items():
            joint = JointConstraint()
            joint.joint_name = name
            joint.position = value
            joint.tolerance_above = joint.tolerance_below = 0.02
            joint.weight = 1.0
            goal.joint_constraints.append(joint)
        plan.goal_constraints = [goal]
        response = self._wait(self.planner.call_async(request), 30).motion_plan_response
        if response.error_code.val != 1:
            raise RuntimeError('MoveIt could not plan to hover')
        trajectory = response.trajectory.joint_trajectory
        endpoint = dict(zip(trajectory.joint_names, trajectory.points[-1].positions))
        mismatched = {name: (round(endpoint[name], 3), round(value, 3))
                      for name, value in target.items()
                      if abs(endpoint[name] - value) > 0.05}
        if mismatched:
            raise RuntimeError(f'MoveIt missed joint goal: {mismatched}')
        for index in range(len(trajectory.joint_names)):
            values = [point.positions[index] for point in trajectory.points]
            # A UR3 wrist can legitimately travel a little over pi radians
            # when returning home.  Reject only a near-full-turn detour.
            if values and max(values) - min(values) > 4.5:
                raise RuntimeError('MoveIt plan winds a joint too far')
        return response.trajectory

    def _execute(self, trajectory):
        goal = ExecuteTrajectory.Goal()
        goal.trajectory = trajectory
        handle = self._wait(self.arm_action.send_goal_async(goal))
        if not handle.accepted:
            raise RuntimeError('MoveIt rejected trajectory')
        result = self._wait(handle.get_result_async(), 120)
        if result.status != GoalStatus.STATUS_SUCCEEDED or result.result.error_code.val != 1:
            raise RuntimeError(f'Arm execution failed: {result.result.error_code.val}')

    def _plan_hover(self, x, y):
        """Plan a collision-safe move to the hover pose without executing it."""
        while self.joints is None:
            rclpy.spin_once(self, timeout_sec=0.2)
        # IK depends on the seed. A small fixed set covers the elbow and
        # shoulder branches that are useful around this tabletop.
        seeds = [(self.joints[ARM[0]], self.joints[ARM[2]])]
        seeds += [(pan, elbow) for pan in (-3.2, -2.5, -1.5, 0.0, 1.0, 2.0, 3.0)
                  for elbow in (-2.0, 0.0, 2.0)]
        for pan, elbow in seeds:
            request = GetPositionIK.Request()
            request.ik_request.group_name = 'ur_manipulator'
            request.ik_request.ik_link_name = 'tool0'
            request.ik_request.pose_stamped = PoseStamped()
            request.ik_request.pose_stamped.header.frame_id = 'world'
            request.ik_request.pose_stamped.pose = self._pose(x, y, PICK_Z)
            request.ik_request.timeout.sec = 2
            request.ik_request.avoid_collisions = False
            request.ik_request.robot_state.is_diff = True
            request.ik_request.robot_state.joint_state.name = list(ARM)
            request.ik_request.robot_state.joint_state.position = [
                pan, self.joints[ARM[1]], elbow, self.joints[ARM[3]],
                self.joints[ARM[4]], self.joints[ARM[5]]]
            response = self._wait(self.ik.call_async(request), 5)
            if response.error_code.val != 1:
                continue
            try:
                upward = self._cartesian(x, y, HOVER_Z, response.solution)
                target = {name: value for name, value in zip(
                    upward.joint_trajectory.joint_names,
                    upward.joint_trajectory.points[-1].positions) if name in ARM}
                while self.joints is None:
                    rclpy.spin_once(self, timeout_sec=0.2)
                trajectory = self._plan_joints(target)
            except RuntimeError:
                continue
            return trajectory
        raise RuntimeError('No reachable hover pose for this cube or target')

    def _move_hover(self, x, y):
        self._table(True)
        try:
            self._execute(self._plan_hover(x, y))
        finally:
            # Do not leave a stale table object in MoveIt after a failed plan or
            # action.  It can make the next retry look like an IK failure.
            self._table(False)

    def _grip(self, position):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(GRIPPER)
        point = JointTrajectoryPoint()
        point.positions = [position, -position, position, -position,
                           -position, position]
        point.time_from_start.sec = int(self.gripper_motion_time)
        point.time_from_start.nanosec = int(
            (self.gripper_motion_time - point.time_from_start.sec) * 1e9)
        goal.trajectory.points = [point]
        handle = self._wait(self.gripper_action.send_goal_async(goal))
        if not handle.accepted:
            raise RuntimeError('Gripper rejected command')
        result = self._wait(handle.get_result_async(), 20)
        if result.status != GoalStatus.STATUS_SUCCEEDED or result.result.error_code != 0:
            raise RuntimeError(f'Gripper execution failed: {result.result.error_code}')

    def open_gripper(self):
        self._grip(0.0)

    def close_gripper(self):
        self._grip(self.gripper_close_position)
        while self.joints is None:
            rclpy.spin_once(self, timeout_sec=0.2)
        left = self.joints['robotiq_85_left_knuckle_joint']
        right = self.joints['robotiq_85_right_knuckle_joint']
        if left > 0.59 and right < -0.59:
            raise RuntimeError('Gripper closed fully; no cube contact detected')

    def pick(self, name):
        if self.held is not None:
            raise RuntimeError('Already holding a cube')
        item = self.state()['objects'].get(name)
        if item is None:
            raise RuntimeError(f'Cube not visible: {name}')
        x, y = item['x'], item['y']
        self.get_logger().info(f'pick {name} from camera ({x:.3f}, {y:.3f})')
        self.open_gripper()
        self._move_hover(x, y)
        self._execute(self._cartesian(x, y, PICK_Z))
        self.close_gripper()
        self._execute(self._cartesian(x, y, HOVER_Z))
        self.held = name

    def place(self, name, target):
        if self.held != name:
            raise RuntimeError(f'Not holding {name}')
        x, y = ZONES[target] if isinstance(target, str) else target
        self.get_logger().info(f'place {name} at ({x:.3f}, {y:.3f})')
        self._move_hover(x, y)
        self._execute(self._cartesian(x, y, PICK_Z))
        self.open_gripper()
        self._execute(self._cartesian(x, y, HOVER_Z))
        self.held = None
        # The arm can hide a released cube from the overhead camera.
        self.home()
        before = time.monotonic()
        deadline = before + 10
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            state = self.environment
            if (state is None or self.environment_time <= before
                    or not state['complete']):
                continue
            item = state['objects'][name]
            if isinstance(target, str):
                confirmed = state['zones'][target] == name
            else:
                confirmed = (item['location'] == 'table'
                             and math.hypot(item['x'] - x, item['y'] - y) < 0.05)
            if confirmed:
                return
            rclpy.spin_once(self, timeout_sec=0.2)
        raise RuntimeError(f'Camera did not confirm {name} at {target}')

    def find_free_position(self):
        """Choose a free cell that is also reachable by the current robot state."""
        state = self.state()
        occupied = [(item['x'], item['y']) for item in state['objects'].values()]
        geometric = []
        for x, y in STAGING_POSITIONS:
            if (all(math.hypot(x - ox, y - oy) > 0.08 for ox, oy in occupied)
                    and all(math.hypot(x - zx, y - zy) > 0.08
                            for zx, zy in ZONES.values())):
                geometric.append((x, y))
        if not geometric:
            raise RuntimeError('No free temporary position on the table')

        failures = []
        for x, y in geometric:
            self._table(True)
            try:
                self._plan_hover(x, y)
            except RuntimeError as exc:
                failures.append(f'({x:.2f},{y:.2f}): {exc}')
                continue
            finally:
                self._table(False)
            return x, y
        details = '; '.join(failures[-3:])
        raise RuntimeError('No reachable temporary position on the table'
                           + (f' ({details})' if details else ''))

    def clear_zone(self, zone):
        if zone not in ZONES:
            raise ValueError(f'Unknown zone: {zone}')
        occupant = self.state()['zones'][zone]
        if occupant is None:
            return
        destination = self.find_free_position()
        self.get_logger().info(f'clear {zone}: move {occupant} to {destination}')
        self.pick(occupant)
        self.place(occupant, destination)
        if self.state()['zones'][zone] is not None:
            raise RuntimeError(f'{zone} remains occupied')

    def home(self):
        if self.held is not None:
            raise RuntimeError('Place the held cube before home')
        self._table(True)
        target = dict(HOME)
        while self.joints is None:
            rclpy.spin_once(self, timeout_sec=0.2)
        # Park the arm above the table without unwinding a full base rotation.
        target['shoulder_pan_joint'] = self.joints['shoulder_pan_joint']
        self._execute(self._plan_joints(target))
