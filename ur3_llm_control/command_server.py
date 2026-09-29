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
from .planning import plan_and_validate
from .student_task import student_mapping, build_trusted_context
from .request_policy import classify_student_request
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
            context=build_trusted_context(state)
            mapping=None
            student_context=None
            config_error=None
            llm_retried=False
            validated=None
            try:
                config=yaml.safe_load(Path(self.get_parameter("student_config").value).read_text())
                if not isinstance(config,dict) or not config.get("student_name") or config["student_name"]=="TODO":
                    raise ValueError("student_config.yaml must contain the student's name and ID")
                xx,p,mapping=student_mapping(config.get("student_id"))
                student_context={"XX":xx,"P":p,"required_mapping":mapping}
            except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
                config_error=str(exc)
            if request.student_task and mapping is None:
                raise ValueError("Strict student-task mode requires a valid config/student_config.yaml: " + (config_error or "invalid identity"))
            if request.plan_json:
                if request.command:
                    raise ValueError("Use either a structured plan or a natural-language command")
                plan=strict_json(request.plan_json)
                student_specific=bool(request.student_task)
                if student_specific and mapping is None:
                    raise ValueError("Strict student-task mode requires a valid config/student_config.yaml: " + (config_error or "invalid identity"))
            else:
                planner=LLMPlanner(self.share/"prompt/planner_prompt.txt")
                student_specific=classify_student_request(
                    planner, request.command, request.student_task, mapping, config_error)
                # Do not show the student mapping while planning an ordinary
                # object-to-zone command.  The mapping is authoritative only
                # after the intent classifier has identified a student task;
                # exposing it for every request makes the model reinterpret a
                # direct command as a mapping conflict and answer with prose.
                plan_context = (build_trusted_context(state,(xx,p,mapping))
                                if student_specific and student_context is not None
                                else context)
                plan,validated,llm_retried=plan_and_validate(
                    planner,request.command,plan_context,state,
                    mapping if student_specific else None)
                if llm_retried:
                    self.get_logger().warning(
                        "Initial LLM plan failed validation; one replacement plan was generated and validated")
            enforced_mapping=mapping if student_specific else None
            if validated is None:
                validated=PlanValidator().validate(plan,state,enforced_mapping)
            report={"command":request.command,"plan":plan,"validation":"VALID",
                    "student_mapping_enforced":student_specific,"required_mapping":enforced_mapping}
            if llm_retried:
                report["llm_retried"]=True
            if request.dry_run:
                report.update({"status":"VALIDATED_ONLY","predicted_state":validated.final_state.__dict__})
            else:
                try:
                    report.update(SkillExecutor(self.backend).execute(plan,enforced_mapping,
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
