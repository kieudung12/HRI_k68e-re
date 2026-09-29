# File inventory

## Created

Project-created files in Assignment 2:

- [.gitignore](../.gitignore)
- [CMakeLists.txt](../CMakeLists.txt)
- [LICENSE](../LICENSE)
- [PROJECT_STATUS.md](../PROJECT_STATUS.md)
- [README.md](../README.md)
- [config/basic_plan.json](../config/basic_plan.json)
- [config/blue_to_c_plan.json](../config/blue_to_c_plan.json)
- [config/robot_skills.yaml](../config/robot_skills.yaml)
- [config/scene.yaml](../config/scene.yaml)
- [config/student_config.yaml](../config/student_config.yaml)
- [config/ur_controllers.yaml](../config/ur_controllers.yaml)
- [docs/FILES.md](../docs/FILES.md)
- [docs/PRESENTATION_GUIDE.md](../docs/PRESENTATION_GUIDE.md)
- [docs/VERIFICATION.md](../docs/VERIFICATION.md)
- [docs/pick_place_verified.json](../docs/pick_place_verified.json)
- [docs/blue_to_c_verified.txt](../docs/blue_to_c_verified.txt)
- [docs/scene_audit_verified.txt](../docs/scene_audit_verified.txt)
- [docs/reset_scene_verified.txt](../docs/reset_scene_verified.txt)
- [docs/blue_to_c_gazebo_poses.txt](../docs/blue_to_c_gazebo_poses.txt)
- [docs/basic_pipeline.txt](../docs/basic_pipeline.txt)
- [docs/gazebo_demo.png](../docs/gazebo_demo.png)
- [docs/gazebo_final_poses.json](../docs/gazebo_final_poses.json)
- [docs/mapping_smoke_verified.json](../docs/mapping_smoke_verified.json)
- [docs/robot_smoke_verified.json](../docs/robot_smoke_verified.json)
- [include/ur3_llm_control/scene_manager.hpp](../include/ur3_llm_control/scene_manager.hpp)
- [launch/application.launch.py](../launch/application.launch.py)
- [launch/llm_robot.launch.py](../launch/llm_robot.launch.py)
- [package.xml](../package.xml)
- [prompt/planner_prompt.txt](../prompt/planner_prompt.txt)
- [scripts/check_scene](../scripts/check_scene)
- [scripts/all_pick_place_test](../scripts/all_pick_place_test)
- [scripts/run_pick_place_suite](../scripts/run_pick_place_suite)
- [scripts/command_cli](../scripts/command_cli)
- [scripts/command_server](../scripts/command_server)
- [scripts/controller_ready](../scripts/controller_ready)
- [scripts/mapping_smoke_test](../scripts/mapping_smoke_test)
- [scripts/planner_integration_test](../scripts/planner_integration_test)
- [scripts/robot_smoke_test](../scripts/robot_smoke_test)
- [scripts/spawn_guard](../scripts/spawn_guard)
- [src/robot_skills_node.cpp](../src/robot_skills_node.cpp)
- [src/scene_manager.cpp](../src/scene_manager.cpp)
- [srv/ExecuteCommand.srv](../srv/ExecuteCommand.srv)
- [srv/ExecuteSkill.srv](../srv/ExecuteSkill.srv)
- [srv/GetState.srv](../srv/GetState.srv)
- [srv/ResetScene.srv](../srv/ResetScene.srv)
- [ur3_llm_control/__init__.py](../ur3_llm_control/__init__.py)
- [ur3_llm_control/command_cli.py](../ur3_llm_control/command_cli.py)
- [ur3_llm_control/command_server.py](../ur3_llm_control/command_server.py)
- [ur3_llm_control/controller_ready.py](../ur3_llm_control/controller_ready.py)
- [ur3_llm_control/llm_planner.py](../ur3_llm_control/llm_planner.py)
- [ur3_llm_control/output_format.py](../ur3_llm_control/output_format.py)
- [ur3_llm_control/planning.py](../ur3_llm_control/planning.py)
- [ur3_llm_control/request_policy.py](../ur3_llm_control/request_policy.py)
- [ur3_llm_control/ros_backend.py](../ur3_llm_control/ros_backend.py)
- [ur3_llm_control/skill_executor.py](../ur3_llm_control/skill_executor.py)
- [ur3_llm_control/student_task.py](../ur3_llm_control/student_task.py)
- [ur3_llm_control/task_validator.py](../ur3_llm_control/task_validator.py)
- [worlds/assignment2.sdf](../worlds/assignment2.sdf)

## Existing files modified

[config/student_config.yaml](../config/student_config.yaml) contains the identity entered by the user: Kieu Minh Dung, 23020729. It is preserved as supplied. The existing [scripts/test_9router.py](../scripts/test_9router.py) is preserved byte-for-byte, including its original trailing blank line. Git whitespace checking excludes that unchanged diagnostic; all newly written text passes.

## Assignment 1 reuse

Read-only reference and minimal adaptation: UR launch composition, controller readiness/hold, six-joint JTC configuration and tested tolerances, current-state synchronization, conservative scaling, joint-angle normalization and Cartesian checks. LICENSE copied. No drawing node, letter-D geometry, marker code, repository history or runtime path dependency copied.
