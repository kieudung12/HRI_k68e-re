# Verification record

Executed on Ubuntu 22.04 / ROS 2 Humble / Gazebo Fortress, 27 September 2026.

| Check | Result | Evidence / scope |
|---|---|---|
| Build: colcon build --symlink-install | PASS | C++17 server, ROS interfaces and Python tools |
| Dependencies: rosdep check | PASS | All system dependencies satisfied; no installation performed |
| Offline tests | PASS | 61 pytest cases; colcon reports 62 tests including the CTest wrapper, zero failures |
| Gazebo startup / controllers / clock / joint states | PASS | Only joint_state_broadcaster and joint_trajectory_controller active |
| MoveGroup runtime model | PASS | world / ur_manipulator / tool0 / six expected joints |
| Collision-aware target IK | PASS | All 12 object/zone grasp and hover targets |
| Complete Cartesian approach | PASS | All six targets; alternate IK seeds used where required |
| Table affects collisions | PASS | Read-only intersecting-state probe rejected, contacts include table |
| Home / pick / place / home | PASS | [Robot report](robot_smoke_verified.json), WORLD/ATTACHED exclusivity and exact final world pose |
| Structured plan -> validator -> executor -> robot | PASS | [CLI output](basic_pipeline.txt), all three skills succeeded |
| Multi-object mapping fixture P=0 | PASS | [Mapping report](mapping_smoke_verified.json); red=A, yellow=B, blue=C, final home |
| Gazebo object synchronization | PASS | [Live pose report](gazebo_final_poses.json), all final poses match config |
| Concurrent command | PASS | Returned BUSY during the multi-object task |
| Invalid final step in plan | PASS | Whole plan rejected; robot revision stayed 17 |
| Unfilled student identity | PASS | Clear rejection before motion |
| Gazebo GUI | PASS | Rendered UR3e/table/cubes/zones; [actual screenshot](gazebo_demo.png) |
| Live English / Vietnamese LLM | NOT VERIFIED | All three NINEROUTER variables missing in this session |
| Student-specific natural-language task | NOT VERIFIED | Real identity and live planner environment missing |
| RViz display | NOT VERIFIED | Gazebo GUI tested; separate RViz option not exercised |
| Fully occupied cyclic rearrangement | Unsupported, safely rejected | No staging skill; tested deterministic refusal |

The P=0 fixture is synthetic test data, not an invented student identity. Earlier
failed trials and fixes remain in PROJECT_STATUS.md. No live LLM result is
claimed from the user's earlier manual diagnostic.

Gazebo scene/info caches spawn poses; verification uses live pose/info. The
screenshot captures the actual simulator after the successful multi-object task;
it is not a generated illustration. Cubes use the explicitly documented virtual
grasp and pose synchronization, not physical finger contact.
