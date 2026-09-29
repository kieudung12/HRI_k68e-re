# Final submission verification

## Recorded review results before removing the unit-test sources (29 September 2026)

The following sections distinguish offline/deterministic robot testing from live language-model and identity-specific behavior. Reset was tested on a fresh stack, including independent Gazebo and MoveIt queries and a second task without restarting Gazebo.

| Area | Current result | Scope |
|---|---|---|
| Deterministic unit tests | PASS at review time: 90 cases | Ran before the test source directory was removed from the submission |
| Python compile check | PASS at review time | `python3 -m compileall -q ur3_llm_control launch test scripts` |
| YAML/JSON parse | PASS: 10 files | All repository YAML/JSON configs and data parsed |
| ROS build/test | PASS at review time: 91 tests, zero failures/errors/skips | Ran before removing the pytest registration and test source directory |
| Deterministic Gazebo/MoveIt motion | PASS | Six fresh scenes; pick/place matrix and invalid-plan rejection |
| ResetScene build | PASS | ROS service interface, CLI and C++ node built |
| ResetScene live runtime | PASS | [Fresh-stack reset test](reset_scene_verified.txt); Gazebo and MoveIt queried independently |
| Post-reset second robot task | PASS | Blue source→zone C→home completed in the same Gazebo process; independent Gazebo/MoveIt readback |
| Live 9Router English/Vietnamese/student planner | Requires user-side verification | Router variables are not configured in the review environment; no live result is claimed |
| Natural-language robot tasks in Gazebo | Requires user-side verification | Do not infer these from structured `--plan-file` regression runs |

After recording these results, the author requested removal of `test/` from the submitted repository. Its Python unit tests and pytest registration have been removed. A fresh `colcon build --symlink-install`, Python compile check for application/launch/scripts, and YAML/JSON parsing passed after that change; the repository no longer contains the unit-test suite.

# Historical verification record

For live verification on the demo machine, first configure 9Router and launch the robot stack as described in the README. In a second sourced terminal, run the planner integration test (it checks live generated plans and validation), then execute the required natural-language commands through `command_cli` (without `--plan-file`):

```bash
ros2 run ur3_llm_control planner_integration_test
ros2 run ur3_llm_control command_cli 'Please put the red cube in zone B.'
ros2 run ur3_llm_control command_cli 'Move the blue cube to zone C.'
ros2 run ur3_llm_control command_cli --student-task 'Arrange all objects according to my student ID.'
```

Reset the scene between tasks when needed. For the student task, verify the final mapping is `blue_cube -> zone_a`, `yellow_cube -> zone_b`, `red_cube -> zone_c`, `held_object=null`, and that the final plan step is `home()`. Record these as PASS only after observing the actual CLI and robot result. Plan files are deterministic pipeline regressions and do not verify 9Router.

## Motion repair verified on 28 September 2026

This section supersedes the older scene/robot-motion results below. Tests used the real Gazebo Fortress server, ros2_control trajectory controller, MoveIt collision checking and the C++ skill services. No robot trajectory was mocked.

The old layout failed because the downward tool orientation puts wrist_1 about 92.1 mm sideways and 85.35 mm below tool0. IK solutions contacted the tabletop or the source cubes behind the trays. The repair moves the workspace in front of the base, lowers the tabletop, uses a 150 mm virtual grasp standoff, derives placement tool poses from the measured attachment transform, and represents tray walls/floors/pedestals in both engines. Tilt retries that used a fixed vertical offset were removed.

| Check | Result | Evidence |
|---|---|---|
| Fresh build + offline regression | PASS (historical, 27 Sep) | 73 pytest cases; colcon reports 74 tests, zero errors/failures/skips |
| Six complete color-to-tray assignments | PASS | [Full machine-readable report](pick_place_verified.json), including the configured P=5 mapping |
| Every source color to every tray (3×3) | PASS | Covered by the six assignments |
| All six directed transfers between distinct trays | PASS | Case 0 re-picks red and traverses A→B→A→C→B→C→A |
| Re-pick and replace each color in the same tray | PASS | Case 2, red in B, yellow in A, blue in C |
| Skill totals | PASS | 27 picks, 27 places, 6 final homes; WORLD/ATTACHED exclusivity and final geometry checked |
| Invalid requests | PASS | 44 expected rejections, with no revision/state mutation; occupied tray, empty-hand place, double pick, home while holding, unknown object/skill/zone |
| Collision-aware grasp/hover IK | PASS | All 12 target poses; [audit log](scene_audit_verified.txt) |
| Deliberate table/obstacle contact | PASS | Invalid state rejected; contact list includes table and tray geometry |
| Full command_cli → validator → executor → robot path | PASS | Blue source→C→home; [CLI output](blue_to_c_verified.txt); no LLM required for this structured-plan regression |
| Independent Gazebo final pose readback | PASS | Blue at (-0.10, 0.24, 0.144); [Gazebo pose topic](blue_to_c_gazebo_poses.txt) |

All motion-suite transits used complete Cartesian routes; no joint-space fallback was needed. Carry routes from sources to trays were about 0.15–0.28 m to hover, followed by the 5 cm descent. This is a short-path preference, not a proof of global optimality. Test stacks ran in isolated ROS domains and were stopped afterward. Reports/logs are also under `log/pick_place_verification/`.

Reproduce after building/sourcing the workspace:

```bash
ros2 run ur3_llm_control run_pick_place_suite --output log/pick_place_verification
```

These are deterministic motion tests, not new live 9Router tests. The virtual grasp remains pose-driven; physical fingers, forces and free falling are not simulated. A fully occupied cyclic rearrangement still needs a staging skill and remains unsupported.

## Earlier verification (27 September 2026)

Executed on Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress, 27 September 2026. Current student configuration is Kieu Minh Dung, ID 23020729 (`XX=29`, `P=5`). The required mapping is Zone A → Blue, Zone B → Yellow, Zone C → Red.

| Check | Result | Evidence / scope |
|---|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test` | PASS | 73 offline cases, including exact real-ID mapping and final-home rules |
| `colcon build --symlink-install` | PASS | C++ backend, generated ROS interfaces, Python and launch files |
| `colcon test` / `colcon test-result --verbose` | PASS | 74 tests, 0 errors, 0 failures, 0 skipped |
| Deterministic 23020729 mapping | PASS | `XX=29`, `P=5`; `zone_a=blue_cube`, `zone_b=yellow_cube`, `zone_c=red_cube` |
| Complete student-plan dry run | PASS | Deterministic feasibility fixture passes `PlanValidator`, reaches the mapping and ends in `home()`; no sequence is sent to the LLM |
| Fresh Gazebo / MoveIt launch | PASS | One clean stack; `/clock` has one publisher; controllers active; startup hold succeeds; scene initialized with gray A/B/C trays |
| Structured basic plan on robot | PASS | `pick(red_cube)`, `place(red_cube, zone_b)`, `home()` each returned SUCCESS through MoveIt/Gazebo |
| Final basic-plan state | PASS | Revision 3, `red_cube=zone_b`, `held_object=null`, `faulted=false` |
| Invalid skill revision probe | PASS | `INVALID_SKILL`; revision stayed 3 |
| Stale revision probe | PASS | Expected revision 2 returned `STALE_STATE`; revision stayed 3 |
| RViz / Gazebo startup | PASS | RViz loaded the robot model; Gazebo GUI plugins and scene loaded |
| Live 9Router English / Vietnamese / student planner | Requires user-side verification | Historical run had no router variables; current review also has no configured router |
| Natural-language student-ID task in Gazebo | Requires user-side verification | No live LLM execution is claimed |
| Earlier P=0 synthetic robot fixture | PASS (prior run) | [Mapping report](mapping_smoke_verified.json); synthetic fixture only, not the configured student's assignment |
| Home/pick/place scene exclusivity | PASS (prior run) | [Robot report](robot_smoke_verified.json), WORLD/ATTACHED queries and final placement pose |
| Occupied full cycle | Unsupported, safely rejected | No staging skill exists; deterministic check refuses before motion |

`safe_order()` is used only for deterministic feasibility tests and smoke fixtures. The normal language path gives the LLM current state and the trusted mapping, uses an LLM intent-classification call, and sends no precomputed skill order to the planner. `--student-task` enforces mapping in validation.

The P=0 report predates this review and is retained as a synthetic regression fixture. The current P=5 real-ID mapping has deterministic test and dry-run validation; actual LLM/Gazebo execution requires user-side verification. The screenshot [gazebo_demo.png](gazebo_demo.png) illustrates the current initialized scene; it is not evidence of a live LLM task.

The machine has previously shown an upstream MoveIt Humble callback-group destruction segmentation fault during Ctrl+C shutdown. This review's basic runtime command completed successfully; the current stack was left running. Start only one stack per ROS domain. Cubes still use the documented virtual grasp and pose synchronization, not physical finger contact.
