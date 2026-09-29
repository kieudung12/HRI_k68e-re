"""Small ROS client; all planning and validation happen in the command server."""
import argparse
import json
from pathlib import Path
import rclpy
from ur3_llm_control.srv import ExecuteCommand, ResetScene
from .output_format import format_execution, format_plan


def main():
    parser = argparse.ArgumentParser(description="UR3 validated skill planner")
    parser.add_argument("command", nargs="?")
    parser.add_argument("--student-task", action="store_true",
                        help="Strict mode: require the student-specific mapping in the validated final state")
    parser.add_argument("--plan-file", type=Path, help="Use structured plan without LLM")
    parser.add_argument("--dry-run", action="store_true", help="Plan and validate without motion")
    parser.add_argument("--reset-scene", action="store_true",
                        help="Move the robot home and return every cube to its original position (no LLM)")
    args = parser.parse_args()
    if args.reset_scene and (args.command or args.student_task or args.plan_file or args.dry_run):
        parser.error("--reset-scene cannot be combined with a command, --student-task, --plan-file, or --dry-run")
    command = args.command or (
        "Arrange all objects according to my student ID."
        if args.student_task and not args.plan_file else "")
    if not args.reset_scene and not command and not args.plan_file:
        command = input("USER COMMAND: ").strip()
    rclpy.init()
    node = rclpy.create_node("command_cli")
    try:
        if args.reset_scene:
            client = node.create_client(ResetScene, "/robot_skills/reset_scene")
            if not client.wait_for_service(timeout_sec=10):
                raise RuntimeError("/robot_skills/reset_scene unavailable; rebuild and restart the robot application once")
            future = client.call_async(ResetScene.Request())
            rclpy.spin_until_future_complete(node, future, timeout_sec=180)
            if not future.done():
                raise RuntimeError("Scene reset timed out; inspect Gazebo and robot state before retrying")
            response = future.result()
            print(response.message)
            if response.state_json:
                print("STATE: " + json.dumps(json.loads(response.state_json), ensure_ascii=False))
            return 0 if response.success else 1
        request = ExecuteCommand.Request(
            command=command, student_task=args.student_task, dry_run=args.dry_run,
            plan_json=args.plan_file.read_text() if args.plan_file else "")
        client = node.create_client(ExecuteCommand, "/llm/command")
        if not client.wait_for_service(timeout_sec=10):
            raise RuntimeError("/llm/command unavailable; launch application first")
        print("USER COMMAND:\n" + (command or "Structured test plan"), flush=True)
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=1800)
        if not future.done():
            raise RuntimeError("Command timed out; robot state unknown. Inspect before retrying")
        response = future.result()
        report = json.loads(response.report_json)
        if "plan" in report:
            title = "LLM PLAN:" if command else "STRUCTURED PLAN:"
            print(f"\n{title}\n{format_plan(report['plan']['plan'])}")
            print("\nVALIDATION:\n" + report["validation"])
            if report.get("llm_retried"):
                print("\nNOTE: The first LLM plan was rejected; a replacement plan passed validation.")
        if "results" in report:
            print("\nEXECUTION:\n" + format_execution(report["results"]))
        if "error" in report:
            print("\nERROR:\n" + report["error"])
        human_status = {
            "TASK_SUCCESS": "TASK SUCCESS",
            "TASK_FAILED": "TASK FAILED",
            "VALIDATED_ONLY": "TASK VALIDATED ONLY",
        }.get(response.status, response.status.replace("_", " "))
        print("\n" + human_status)
        if "state" in report:
            print("FINAL STATE: " + json.dumps(report["state"], ensure_ascii=False))
        return 0 if response.status in ("TASK_SUCCESS", "VALIDATED_ONLY") else 1
    except (RuntimeError, ValueError, OSError) as exc:
        print("TASK_FAILED: " + str(exc))
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
