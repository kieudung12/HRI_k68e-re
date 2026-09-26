# UR3 LLM Assignment 2 - Project Status

## Current status
Implementation and deterministic robot integration are working. **PASS**: home, pick/place, complete structured-plan pipeline, and three-object P=0 fixture in Gazebo. **NOT VERIFIED**: live LLM and real student-ID task because this session lacks router environment variables and the student configuration remains TODO. Final build and all available tests passed. Verification simulators/GUI were stopped after testing. Local commit preparation is the only remaining engineering step; no push authorized or performed.

## Completed
- Audited Assignment 1 read-only and compared its launch/source against the requested GitHub main reference.
- Self-contained ament_cmake C++17 package with Python planner, strict schema/semantic validator, student mapping, sequential executor and ROS command/skill/state services.
- MoveIt collision-aware IK, complete approach preplanning, Cartesian collision/jump checks, angle unwrapping, retiming and explicit statuses.
- Native SceneManager, table/cubes/zones, exclusive WORLD/ATTACHED transitions, Gazebo TF-based simulated grasp synchronization.
- ROS-native controller recovery/hold and guarded spawn retry; only JSB and JTC active.
- CLI, structured-plan diagnostic, offline tests and separate live/robot integration diagnostics.
- README, evidence reports and actual Gazebo screenshot in docs/.

## In progress
Creating the reviewed local assignments_2 commit. Implementation, documentation and available runtime verification are complete.

## Remaining
- User must fill real student_name and student_id in config/student_config.yaml.
- User must export NINEROUTER_BASE_URL, NINEROUTER_API_KEY and NINEROUTER_MODEL in the server launch terminal.
- Run live English/Vietnamese and actual student-ID end-to-end demos; add video link; review before pushing.
- Occupied permutation cycles have no staging support and are deliberately rejected. Free-destination reordering is implemented/tested.

## Environment discovered
Ubuntu 22.04.5; ROS 2 Humble; MoveIt 2.5.10; Gazebo Fortress 6.18.0. UR simulation comes from the normal ~/ros2_ws installation; MoveIt/UR/ros_gz and native Ignition dependencies are installed. `rosdep check` reports all dependencies satisfied. No packages installed.
Runtime planning group ur_manipulator, frame world, end-effector tool0, obtained from MoveGroup. Six joints: shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint. Both robot descriptions and KDL kinematics available. No simulated gripper joints/controller exists. Trajectory action: /joint_trajectory_controller/follow_joint_trajectory.

## Architecture decisions
The LLM only returns allowed skills; it has no MoveIt/controller capability. Python validates the whole plan before execution and verifies returned logical state/revisions. ROS services connect to a serialized C++ MoveGroup backend; MoveIt feedback spins independently. Simulated grasp uses native collision attachment and explicit Gazebo pose synchronization; it does not claim physical grasping. Startup's fixed controller hold is isolated from task planning. No runtime path references Assignment 1.

## Files created / changed
See docs/FILES.md for the exact inventory. All implementation files are new in Assignment 2. Existing scripts/test_9router.py is preserved unchanged. Assignment 1 remains clean on main with its original remote untouched.

## Commands executed
```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test
colcon test-result --verbose
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test
rosdep check --from-paths . --ignore-src --rosdistro humble
ros2 launch ur3_llm_control llm_robot.launch.py
ros2 control list_controllers
ros2 run ur3_llm_control check_scene
python3 scripts/robot_smoke_test --report log/verification/robot_smoke_verified.json
ros2 run ur3_llm_control command_cli --plan-file config/basic_plan.json
python3 scripts/mapping_smoke_test --permutation 0 --report log/verification/mapping_smoke.json
python3 scripts/planner_integration_test
```
Also executed read-only MoveIt/Gazebo scene, TF and collision probes; ROS negative/concurrency tests; a temporary reference clone; git status/branch/remote and staged-secret checks. Logs are ignored under log/verification; selected evidence is in docs/.

## Tests
- **PASS**: 61 pytest cases; colcon summary 62 tests including CTest wrapper, zero errors/failures/skips.
- **PASS**: build, dependency resolution, package executable discovery, Python syntax checks.
- **PASS**: simulation startup, active JSB/JTC, descriptions, /clock and /joint_states.
- **PASS**: all 12 collision-aware endpoint IK checks and all six full approach paths; table collision rejection.
- **PASS**: direct home/pick/place/home and WORLD/ATTACHED exclusivity; exact MoveIt placement coordinates.
- **PASS**: structured basic pipeline TASK_SUCCESS; three-object P=0 fixture TASK_SUCCESS, final home/revision 17.
- **PASS**: Gazebo live poses match red=A, yellow=B, blue=C; actual GUI rendering screenshot saved.
- **PASS**: BUSY concurrency rejection; invalid later step causes zero motion/revision change; TODO identity rejected clearly.
- **NOT VERIFIED**: English/Vietnamese live LLM, actual student-ID LLM-to-robot task. All three NINEROUTER variables absent. The original manually tested router script is retained, not claimed as newly verified.
- **NOT VERIFIED**: RViz display option.
- **FAIL (historical, fixed)**: initial pytest plugin incompatibility, test/CLI syntax, executable permission, duplicate spawn/orphan server, colliding IK branch, partial Cartesian approach, redundant world removal during attach, Cartesian 2*pi wrap and smoke-test coordinate interpretation. Detailed history follows. No unresolved failure in the final tested robot pipeline.

## Problems encountered
See milestone history. A host/session restart removed /tmp logs and stopped the simulator; persistent verification logs now live under the project. Missing router environment/identity prevents remaining live tests.

## Solutions / decisions
Use the verified C++ MoveIt stack, explicit collision-aware approach planning and conservative 0.05 scaling. Full-plan and returned-state checks stop failures. Resolve supported occupied zones using free destinations; reject cycles before motion. Preserve Assignment 1, do not install unrelated packages, do not push.

## Next exact step
Create the local commit, then the user fills identity/router environment and runs the documented live demos before reviewing and pushing assignments_2.

## Milestone history

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
- Student identity not established: use TODO until supplied.
- Assignment 1 main is clean and has a different remote (HRI_b1); leave it unchanged. Requested submission repository has only main. Assignment 2 has no Git repository.

## Architecture decision after audit
Use ament_cmake C++17 MoveGroupInterface plus pure Python planner/validator/executor. ROS services transport commands and skills. C++ SceneManager owns collision geometry and explicit Ignition Transport pose synchronization for simulated grasp. Arm motion always uses MoveIt. Only one trajectory controller is configured. Full-plan semantic validation precedes execution, and state revisions guard stale requests.

## Next exact step
PHASE 1/2: create package skeleton, strict planner, semantic validator, deterministic student mapping and offline tests; preserve existing diagnostic.

## Milestone: PHASE 1/2 implemented; PHASE 3 verification running
Created package manifest/CMake/interfaces, prompt, scene/skill/student configurations, planner, semantic validator, sequential executor and student mapping. Student fields remain TODO. Existing test_9router.py unchanged.
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

## Milestone: PHASE 11/12 verified handoff
- PASS: multi-object fixture P=0 completed all seven skills, final home, held_object=null, faulted=false, red_cube=zone_a, yellow_cube=zone_b, blue_cube=zone_c (revision 17).
- PASS: live Gazebo pose/info independently matches all three final coordinates. Gazebo GUI rendered the actual robot, table, cubes and zones; screenshot saved in docs/gazebo_demo.png.
- PASS: concurrent dry-run request returned BUSY; malformed later plan step rejected with unchanged revision; TODO identity rejected before motion.
- PASS: colcon test-result reports 62 tests (61 pytest cases plus CTest wrapper), zero errors/failures/skips.
- PASS: staged-file hygiene and credential-pattern scan; build/install/log/.env excluded. Full final scan and local commit remain.
- RViz display remains NOT VERIFIED. No physical gripper, vision, or staging-area claim.


## Final verification before local commit
- PASS: final `colcon build --symlink-install` (1 package), `colcon test`, and `colcon test-result --verbose`: 62 tests, 0 errors, 0 failures, 0 skipped.
- PASS: syntax checks for all source/entrypoints; 50 tracked candidates, no build/install/log/.env or credential patterns. Original diagnostic is byte-for-byte preserved; its pre-existing extra blank line is excluded from new-file whitespace checking.
- PASS: native Gazebo shutdown acknowledged after successful robot/GUI tests; test stack stopped to avoid competing with the user's next demo.
- Inventory: 49 created files, 1 preserved existing diagnostic, 0 existing files modified. Assignment 1 remains unchanged.
- Evidence: docs/VERIFICATION.md, docs/FILES.md, robot/mapping JSON reports, live Gazebo poses, CLI output and actual GUI screenshot.
- NOT VERIFIED remains live LLM / real student identity / RViz display. No unresolved failure in the tested deterministic robot pipeline; no physical gripper or occupied-cycle staging claimed.
