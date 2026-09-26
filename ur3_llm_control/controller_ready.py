"""Finite startup recovery using ROS APIs; never used by the LLM executor."""
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from controller_manager_msgs.srv import ListControllers, LoadController, ConfigureController, SwitchController
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

def wait(node, future, seconds=5):
    rclpy.spin_until_future_complete(node,future,timeout_sec=seconds)
    if not future.done(): raise RuntimeError("Controller operation timed out")
    return future.result()

def main():
    rclpy.init()
    node=Node("controller_ready")
    clients={name:node.create_client(kind,"/controller_manager/"+name) for name,kind in
             [("list_controllers",ListControllers),("load_controller",LoadController),
              ("configure_controller",ConfigureController),("switch_controller",SwitchController)]}
    deadline=time.monotonic()+120
    required=("joint_state_broadcaster","joint_trajectory_controller")
    try:
        while time.monotonic()<deadline:
            if not clients["list_controllers"].wait_for_service(timeout_sec=1): continue
            status={c.name:c.state for c in wait(node,clients["list_controllers"].call_async(ListControllers.Request())).controller}
            if status.get("scaled_joint_trajectory_controller")=="active":
                raise RuntimeError("Competing scaled controller is active")
            if all(status.get(c)=="active" for c in required): break
            for c in required:
                if c not in status:
                    request=LoadController.Request(); request.name=c
                    response=wait(node,clients["load_controller"].call_async(request))
                    if not response.ok: node.get_logger().warn(f"Load {c} failed; retrying readiness")
                elif status[c]=="unconfigured":
                    request=ConfigureController.Request(); request.name=c
                    response=wait(node,clients["configure_controller"].call_async(request))
                    if not response.ok: node.get_logger().warn(f"Configure {c} failed")
                elif status[c]=="inactive":
                    request=SwitchController.Request(); request.activate_controllers=[c]; request.strictness=2
                    request.timeout.sec=3
                    response=wait(node,clients["switch_controller"].call_async(request))
                    if not response.ok: node.get_logger().warn(f"Activate {c} failed")
            time.sleep(0.5)
        else: raise RuntimeError("Controllers not ready within 120 seconds")
        # Proven Assignment 1 startup hold prevents gravity drift before MoveIt
        # receives its first task. This fixed startup action is never LLM-controlled.
        action=ActionClient(node,FollowJointTrajectory,"/joint_trajectory_controller/follow_joint_trajectory")
        if not action.wait_for_server(timeout_sec=10): raise RuntimeError("Trajectory action unavailable")
        goal=FollowJointTrajectory.Goal()
        goal.trajectory.joint_names=["shoulder_pan_joint","shoulder_lift_joint","elbow_joint","wrist_1_joint","wrist_2_joint","wrist_3_joint"]
        point=JointTrajectoryPoint(); point.positions=[0.,-1.57,0.,-1.57,0.,0.]; point.time_from_start.sec=1
        goal.trajectory.points=[point]
        handle=wait(node,action.send_goal_async(goal))
        if not handle.accepted: raise RuntimeError("Startup hold rejected")
        result=wait(node,handle.get_result_async(),30).result
        if result.error_code != 0: raise RuntimeError("Startup hold failed: "+result.error_string)
        node.get_logger().info("READY: controllers active; startup hold SUCCESS")
        return 0
    except Exception as exc:
        node.get_logger().error(str(exc)); return 1
    finally:
        node.destroy_node(); rclpy.shutdown()
