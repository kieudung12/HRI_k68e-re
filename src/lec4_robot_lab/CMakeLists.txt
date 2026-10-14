cmake_minimum_required(VERSION 3.8)
project(lec4_robot_lab)
find_package(ament_cmake REQUIRED)
install(DIRECTORY launch config maps worlds DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/drive_wasd.py
  scripts/gazebo_session.py
  scripts/initial_pose_relay.py
  scripts/amcl_tf_watchdog.py
  scripts/ensure_localization_active.py
  scripts/wait_localization_ready.py
  scripts/scan_throttle.py
  scripts/runtime_guard.py
  DESTINATION lib/${PROJECT_NAME})
install(FILES README.md DESTINATION share/${PROJECT_NAME})
ament_package()
