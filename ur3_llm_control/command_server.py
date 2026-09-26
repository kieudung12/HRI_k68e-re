"""ROS command boundary: natural language -> planner -> validator -> executor."""
import json
import threading
from pathlib import Path
import yaml
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from ament_index_python.packages import get_package_share_directory
from ur3_llm_control.srv import ExecuteCommand
from .llm_planner import LLMPlanner, strict_json
from .task_validator import PlanValidator
from .student_task import student_mapping, safe_order
from .skill_executor import SkillExecutor
from .ros_backend import ROSBackend

class CommandServer(Node):
    def __init__(self):
        super().__init__("llm_command_server")
        self.share=Path(get_package_share_directory("ur3_llm_control"))
        self.declare_parameter("student_config",str(self.share/"config/student_config.yaml"))
        self.group=ReentrantCallbackGroup()
        self.backend=ROSBackend(self,self.group)
        self.lock=threading.Lock()
        self.uncertain=False
        self.service=self.create_service(ExecuteCommand,"/llm/command",self.command,callback_group=self.group)

    def command(self,request,response):
        if not self.lock.acquire(blocking=False):
            response.status="BUSY";response.report_json=json.dumps({"error":"Another command is running"});return response
        try:
            if self.uncertain:
                raise RuntimeError("Previous transport failure left execution uncertain; inspect and restart the application")
            state=self.backend.state()
            mapping=None
            context={"held_object":state.held_object,"object_locations":state.object_locations,
                     "zone_occupancy":state.zone_occupancy}
            if request.student_task:
                config=yaml.safe_load(Path(self.get_parameter("student_config").value).read_text())
                if not config.get("student_name") or config["student_name"]=="TODO":
                    raise ValueError("Fill student_name and student_id in config/student_config.yaml before demo")
                xx,p,mapping=student_mapping(config["student_id"])
                feasible=safe_order(mapping,state)
                context.update({"XX":xx,"P":p,"required_mapping":mapping,"feasible_skill_order":feasible["plan"]})
            if request.plan_json:
                if request.command:
                    raise ValueError("Use either a structured plan or a natural-language command")
                plan=strict_json(request.plan_json)
            else:
                plan=LLMPlanner(self.share/"prompt/planner_prompt.txt").plan(request.command,context)
            validated=PlanValidator().validate(plan,state,mapping)
            report={"command":request.command,"plan":plan,"validation":"VALID","required_mapping":mapping}
            if request.dry_run:
                report.update({"status":"VALIDATED_ONLY","predicted_state":validated.final_state.__dict__})
            else:
                try:
                    report.update(SkillExecutor(self.backend).execute(plan,mapping,
                        lambda step,status:self.get_logger().info(f"{step}: {status}")))
                except RuntimeError:
                    self.uncertain=True
                    raise
            response.status=report["status"];response.report_json=json.dumps(report,ensure_ascii=False)
        except Exception as exc:
            # Planner errors deliberately omit response bodies/headers and credentials.
            self.get_logger().error(f"Command rejected: {type(exc).__name__}: {exc}")
            response.status="TASK_FAILED";response.report_json=json.dumps({"error":str(exc)},ensure_ascii=False)
        finally:
            self.lock.release()
        return response

def main():
    rclpy.init();node=CommandServer();executor=MultiThreadedExecutor(num_threads=4);executor.add_node(node)
    try: executor.spin()
    except KeyboardInterrupt: node.get_logger().info("Command server stopped")
    finally:
        executor.shutdown();node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
