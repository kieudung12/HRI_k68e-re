# Gói bài thực hành 04

Gói này cung cấp một world Gazebo nhỏ, cấu hình SLAM Toolbox, các launch gọn để gọi stack TurtleBot 4 có sẵn, và teleop WASD chạy trong terminal.

Hướng dẫn chạy nằm trong [README workspace](../../README.md). `spawn_robot.launch.py` gọi robot description, bridge và controller chính thức để spawn TurtleBot tại tâm phòng `(0, 0)`, yaw `0`; không tạo dock hoặc gọi undock.

Navigation dùng một Gazebo và một lệnh `nav.launch.py nav2:=true rviz:=true`. AMCL chờ **2D Pose Estimate**; `initial_pose_relay.py` đóng dấu pose theo odometry gần nhất và `wait_localization_ready.py` chờ TF `map → odom` mới. RViz phải giữ panel **Navigation 2**, vì GoalTool trong Nav2 Humble chuyển goal qua panel này tới action server.

`diffdrive_controller` phát `/odom` và TF `odom → base_link`; AMCL dùng `map`, `odom`, `base_link`. Dừng Nav2/localization trước Gazebo để không giữ TF buffer cũ khi `/clock` reset. Launch chặn các instance SLAM/localization/Nav2 trùng và yêu cầu simulator đang chạy.

Chạy `bash setup_runtime.sh` ở workspace trước lần chạy đầu tiên để build `tf2_ros 0.25.22` chính thức. Môi trường lab nạp thư viện này riêng cho phiên mô phỏng.
