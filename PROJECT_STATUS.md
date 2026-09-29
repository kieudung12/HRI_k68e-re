# UR3 LLM Assignment 2 - Project Status

## Current status (29 September 2026)

This is the authoritative submission status; milestone notes below are historical. The original UR3e / Gazebo Fortress / MoveIt architecture is retained. Configured identity: Kieu Minh Dung, ID 23020729 (`XX=29`, `P=5`); mapping: zone A=blue, zone B=yellow, zone C=red.

- Motion regression: PASS — six fresh Gazebo runs, all 27 pick/place pairs and 44 expected invalid-request rejections; see [verification](docs/VERIFICATION.md).
- Automated unit-test source has been removed from the submission at the user's request. The package build and runtime interfaces remain part of the deliverable.
- ResetScene build/runtime: PASS. Independent Gazebo and MoveIt source-pose checks passed; a blue→zone C task then succeeded in the same Gazebo process. Evidence: [reset runtime record](docs/reset_scene_verified.txt).
- Live 9Router English/Vietnamese tests and student-ID LLM-to-Gazebo task: requires user-side verification; the review shell has no `NINEROUTER_BASE_URL`, `NINEROUTER_API_KEY`, or `NINEROUTER_MODEL` configured.
- Empty LLM plan is treated as a refusal and rejected before retry or robot execution. CLI plan and execution output share one formatter.
- This review has not pushed changes. Current branch: `assignments_2`.

The scene uses a 0.40 x 0.36 m table at z=0.06 m, source cubes at y=0.33 m, and 9 cm raised trays at y=0.24 m. Gazebo and MoveIt share the table, cube and tray collision geometry. Pick/place prefer short, collision-checked Cartesian routes; global optimality is not claimed. Simulated grasp uses pose synchronization because the UR3e model has no physical gripper.

## Revision semantics
The C++ service's `revision` versions authoritative state. A successfully completed `home`, `pick`, or `place` increments once. If an accepted motion fails in a way that may have moved the arm or changed attachment state, `faulted` is latched and the revision advances once for that fault transition. Subsequent invalid/stale diagnostic calls do not alter the revision. This preserves stale-state protection and prevents invalid skill requests from creating fake state versions.

## Natural-language demo commands
In terminal 1, source and start one stack:

```bash
cd ~/HRI/ur3_LLM_b2
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
source install/setup.bash
ros2 launch ur3_llm_control llm_robot.launch.py
```

Launch from a terminal where the three `NINEROUTER_*` variables are already set; terminal 2 then sends the natural-language command below. Variables exported only in terminal 2 do not reach a command server already running in terminal 1. A demo command uses the natural-language path through 9Router and does not use `--plan-file`:

```bash
cd ~/HRI/ur3_LLM_b2
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
source install/setup.bash
ros2 run ur3_llm_control command_cli 'Arrange all objects according to my student ID.'
```

The deterministic `--plan-file` examples are regression/smoke tests only. The live language-model test commands and their current verification state are recorded in [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## Historical implementation milestones

## Milestone: PHASE 0 audit complete
- PASS: inspected local Assignment 1 package, launch, controllers and MoveIt source read-only; temporary clone of requested repository succeeded (main c997f54).
- Ubuntu 22.04.5, ROS Humble, ament_cmake/C++17, MoveIt 2.5.10, Gazebo Fortress 6.18.0.
- ur_simulation_gz available from the normal ~/ros2_ws overlay; ur_moveit_config and ros_gz packages installed. No dependency installation required so far.
- KDL IK configured for ur_manipulator. SRDF ends at tool0; actual MoveGroup runtime frame/link NOT VERIFIED yet.
- No running simulation, descriptions, joint states, actions or controller_manager at audit time. Controller query timed out (expected before launch).
- Model has no gripper joints or controller. Installed generic gripper_controllers is not a configured gripper.
- Expected joints: shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint.
- Expected controllers: joint_state_broadcaster and joint_trajectory_controller; action /joint_trajectory_controller/follow_joint_trajectory.
- Tool0 +Z is forward per installed URDF. Downward quaternion will be verified against runtime FK, IK and collisions.
- 9Router /v1/models HTTP 200; all NINEROUTER environment variables absent. Live authenticated planner NOT VERIFIED. Asked for an existing env-file path, never the key.
- At that initial audit no identity had been supplied; the current configured identity is documented in Current status above.
- Assignment 1 main is clean and has a different remote (HRI_b1); leave it unchanged. Requested submission repository has only main. Assignment 2 has no Git repository.

## Architecture decision after audit
Use ament_cmake C++17 MoveGroupInterface plus pure Python planner/validator/executor. ROS services transport commands and skills. C++ SceneManager owns collision geometry and explicit Ignition Transport pose synchronization for simulated grasp. Arm motion always uses MoveIt. Only one trajectory controller is configured. Full-plan semantic validation precedes execution, and state revisions guard stale requests.

## Next exact step
PHASE 1/2: create package skeleton, strict planner, semantic validator, deterministic student mapping and offline tests; preserve existing diagnostic.

## Milestone: PHASE 1/2 implemented; PHASE 3 verification running
Created package manifest/CMake/interfaces, prompt, scene/skill/student configurations, planner, semantic validator, sequential executor and student mapping. At initial implementation the student fields were not yet supplied. Existing test_9router.py remained unchanged.
- Validator rejects unknown fields, bad skills/objects/zones, invalid held state, occupied destinations, incomplete plans, faults and wrong student mapping before execution.
- Advanced safe reordering uses free zones; fully occupied permutation cycles explicitly fail before motion (no staging skill). This limitation will be documented.
- FAIL (environment): initial pytest invocation loaded an incompatible user-installed anyio plugin (`_pytest.scope` missing). Retrying with unrelated third-party plugin autoload disabled; no system packages changed.
- PHASE 3: initial ROS interface build in progress.

## Milestone: PHASE 2/3 deterministic verification
- PASS: 56 deterministic pytest tests after correcting a test decorator typo and disabling the incompatible external plugin.
- PASS: initial ament/ROS service generation build.
- Added ROS-native controller readiness/recovery and fixed startup hold adapted from Assignment 1. Minimal controller config keeps only JSB and JTC, retaining tested jitter tolerances.
- Added simulation launch and duplicate-safe delayed spawn retry. Application remains empty during PHASE 4 stack verification.
- Full colcon build/test rerun in progress. No live robot motion claimed yet.

## Next exact step
PHASE 4: launch Gazebo and MoveIt without application, inspect controllers, descriptions and joint state; then implement and test home.

## Milestone: PHASE 4/5 startup diagnosis
- PASS: colcon build and colcon test (56 pytest cases; colcon summary 57 tests, zero failures).
- FAIL then fixed: controller_ready was not executable under symlink install; set executable mode.
- PASS: controller readiness and startup hold completed; /joint_states and both description topics observed.
- PASS: actual MoveGroup planning frame world, end-effector tool0, expected six joints confirmed at runtime.
- FAIL: first home planned but execution aborted (trajectory action server unavailable). A Gazebo child survived the initial failed launch and captured subsequent spawn/controller startup. Stopped the confirmed orphan; restarting cleanly on a new partition.
- NOT VERIFIED: home execution, pick/place and scene reachability until clean restart.

## Milestone: PHASE 5 home verified
- PASS: MoveIt home() planned and executed successfully via /robot_skills/execute, status SUCCESS, faulted=false.
- Root cause of frozen simulation found: unconditional spawn retry could create a second robot; added native ROS graph guard and explicit -allow_renaming=false.
- Controller recovery works, but official spawners can still report benign configure races when recovery has already activated them. Will reduce this race before final cleanup.
- No 3D sensor/octomap plugin is expected: assignment uses deterministic collision objects, no camera.
- Next: PHASE 6 table/cubes/zones and collision scene; validate every approach/grasp pose, then PHASE 7/8 pick/place.

## Milestone: PHASE 6 scene and reachability verified
- PASS: Gazebo scene creation and native set_pose acknowledgments for three cubes; table and zone markers generated from scene.yaml.
- PASS: MoveIt world collision IDs exactly table, red_cube, yellow_cube, blue_cube; no attachments initially.
- PASS: collision-aware /compute_ik for all 12 object/zone grasp/hover targets with configured downward quaternion and actual tool0.
- Fixed compile mismatch between std::vector and ROS bounded dimensions vector; rebuilt successfully.
- Scene uses 4 cm cubes, tabletop z=0.12 m, 3 mm clearance, a documented virtual 10 cm grasp offset and 8 cm approach height.
- Pick/place implemented using normal MoveIt pose plans plus complete collision-checked Cartesian segments, joint-jump checks and explicit conservative retiming. Runtime tests next.

## PHASE 7 first pick trial
- FAIL safely: pick(red_cube) returned PLANNING_FAILED before motion because local setJointValueTarget IK selected a colliding solution although collision-free solutions exist.
- Decision: use /compute_ik with avoid_collisions=true and current-state seed, then normalize joint revolutions and plan the validated joint target. This preserves collision checks throughout; no collision exemptions added.

## PHASE 7 approach correction
- Second pick reached hover but correctly refused a partial Cartesian descent (fraction 0.118); no grasp was claimed.
- Added complete reverse-approach preplanning and bounded IK seed retries before arm movement; execute the checked reversed path with fresh retiming.
- Start-state messages now explicitly preserve Planning Scene attachments (`is_diff=true`).
- A temporary diagnostic initially left quaternion.w at this installation's default 1.0 while setting x=1.0; corrected it to exact [1,0,0,0]. This was a probe error, not a change to configured robot orientation.
- Original scene coordinates are retained pending the corrected full-path audit. No arbitrary layout change accepted.

## PHASE 7 attachment diagnosis
- PASS: corrected approach audit found complete paths for all original targets; no coordinate changes needed.
- PASS: pick reached hover and descended through MoveIt using the prevalidated trajectory.
- FAIL: attach returned GRASP_FAILED because the diff redundantly removed the world object after MoveIt had already removed it automatically during attachment. Robot stopped and faulted; no false success claimed.
- Fix: use the native attached-object ADD transition alone, then verify world absence and attached presence. MoveIt performs the world removal atomically.

## Runtime session interruption
The host session was restarted: simulation processes and /tmp logs disappeared. Workspace files remain. The last launched smoke test has no retrievable result and is NOT VERIFIED. Restarting the compiled attachment fix; new logs go to log/verification inside the project.


## Milestone: PHASE 7 PASS; PHASE 8 final retreat diagnosis
- PASS: direct home and pick(red_cube); full approach, descent, WORLD -> ATTACHED verification, and attached retreat all succeeded.
- Place reached zone_b, detached and verified ATTACHED -> WORLD successfully.
- FAIL: place's final retreat hit controller position tolerance because a Cartesian wrist angle differed by exactly 2*pi. Executor correctly stopped; scene state records red_cube in zone_b.
- Fix: unwrap every Cartesian trajectory point relative to the measured joints, including the first point, before jump checks and retiming. No tolerance widening.
- PASS: 61 offline tests including inconsistent state and false-success detection. rosdep check: all system dependencies satisfied.

## Milestone: PHASE 7/8 robot skills PASS
- PASS: home, pick(red_cube), place(red_cube, zone_b), including full retreat, all returned SUCCESS after Cartesian angle unwrapping.
- PASS: WORLD -> ATTACHED -> WORLD verified by independent Planning Scene queries; state held_object=null and red_cube=zone_b.
- FAIL (test instrumentation only): smoke test treated primitive-local coordinates as world coordinates. MoveIt canonicalizes placement into CollisionObject.pose, with primitive pose at the origin. Corrected the test to compose both transforms; robot execution itself succeeded.
- Next: rerun the corrected smoke test, then structured-plan validator/executor integration and multi-object mapping.

## Milestone: PHASE 7/8 complete; PHASE 9 integration
- PASS: corrected robot_smoke_test completed home -> pick(red_cube) -> place(red_cube, zone_b) -> home, all SUCCESS, with attachment exclusivity and exact composed world-position verification.
- Report: log/verification/robot_smoke_verified.json (PASS).
- Fixed CLI print-string syntax and verified all 20 Python source/entrypoint files parse. Rebuilt installed Python modules; command_cli --help PASS.
- Structured JSON -> ROS command server -> validator -> sequential executor -> MoveIt test now running.
- Local independent Git repository initialized on assignments_2 with requested origin; Assignment 1 main remains clean. No push performed.

## Milestone: PHASE 9 PASS; PHASE 10/11 status
- PASS: config/basic_plan.json through /llm/command -> independent validator -> sequential executor -> ROS skills -> MoveIt completed pick/place/home with TASK_SUCCESS.
- PASS: live Gazebo /world/assignment2/pose/info reports red_cube at [0.30, -0.17, 0.143], matching zone_b and the MoveIt world geometry. scene/info contains cached spawn poses; use live pose/info for verification.
- PHASE 10 NOT VERIFIED: reusable English/Vietnamese live planner test exits with explicit missing NINEROUTER_BASE_URL, NINEROUTER_API_KEY, NINEROUTER_MODEL. No secret requested in chat or stored.
- PHASE 11: deterministic six mappings and occupied-zone ordering already unit-tested. Multi-object robot integration running with synthetic P=0 fixture, without modifying student_config.yaml.
- Added reproducible robot_smoke_test, mapping_smoke_test, planner_integration_test; preserved original standalone test_9router.py.

## Historical milestone: PHASE 11/12 verified handoff
- PASS: multi-object fixture P=0 completed all seven skills, final home, held_object=null, faulted=false, red_cube=zone_a, yellow_cube=zone_b, blue_cube=zone_c (revision 17).
- PASS: live Gazebo pose/info independently matches all three final coordinates. Gazebo GUI rendered the actual robot, table, cubes and zones; screenshot saved in docs/gazebo_demo.png.
- PASS: concurrent dry-run request returned BUSY; malformed later plan step rejected with unchanged revision; then-unconfigured TODO identity rejected before motion.
- PASS: colcon test-result reports 62 tests (61 pytest cases plus CTest wrapper), zero errors/failures/skips.
- PASS: staged-file hygiene and credential-pattern scan; build/install/log/.env excluded. Full final scan and local commit remain.
- RViz display was NOT VERIFIED at that earlier handoff. No physical gripper, vision, or staging-area claim.


## Historical final verification before the student configuration was supplied
- PASS: final `colcon build --symlink-install` (1 package), `colcon test`, and `colcon test-result --verbose`: 62 tests, 0 errors, 0 failures, 0 skipped.
- PASS: syntax checks for all source/entrypoints; 50 tracked candidates, no build/install/log/.env or credential patterns. Original diagnostic is byte-for-byte preserved; its pre-existing extra blank line is excluded from new-file whitespace checking.
- PASS: native Gazebo shutdown acknowledged after successful robot/GUI tests; test stack stopped to avoid competing with the user's next demo.
- At that earlier handoff, the inventory recorded 49 created files, 1 preserved existing diagnostic, and 0 existing files modified. Those counts describe the earlier snapshot only. Assignment 1 remains unchanged.
- Evidence: docs/VERIFICATION.md, docs/FILES.md, robot/mapping JSON reports, live Gazebo poses, CLI output and actual GUI screenshot.
- At that earlier handoff, live LLM, real student identity, and RViz were NOT VERIFIED. The current review status is in the section at the top of this file.
