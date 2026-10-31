# Thành phần bên thứ ba

- ROS 2 Humble, Nav2, TurtleBot 4 và Gazebo Fortress được cài từ hệ thống. B7 có launch và world riêng, sử dụng robot, bridges và bộ điều hướng chuẩn từ các package này.
- `config/nav2.yaml` và `config/map.rviz` bắt đầu từ các cấu hình mặc định trong `nav2_bringup`, rồi điều chỉnh frame, kích thước robot, scan, pose khởi tạo và tần số điều khiển. Nav2: https://github.com/ros-navigation/navigation2 (Apache-2.0).
- `setup_runtime.sh` tải và build `tf2_ros` của ROS geometry2 0.25.22, commit `65c620c308920f558c7b5d3fb852941bd6d8fced`, bên trong `.runtime`. Geometry2: https://github.com/ros2/geometry2 (BSD-3-Clause).
- Model Whisper large-v3 gốc của OpenAI được SYSTRAN chuyển sang CTranslate2. Model: https://huggingface.co/Systran/faster-whisper-large-v3 ; mã inference: https://github.com/SYSTRAN/faster-whisper (MIT). Revision model được khóa trong script tải.
- Âm thanh thử trong `evidence/audio` là giọng tiếng Việt tổng hợp. `cases.json` ghi câu yêu cầu và tuyến mong đợi. Với C/D, văn bản gửi cho TTS viết “xê”/“đê” để tránh bộ TTS tự đọc chữ cái thành số La Mã 100/500.
