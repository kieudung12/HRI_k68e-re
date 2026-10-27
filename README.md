# Bài thực hành 06 — Điều khiển TurtleBot 4 bằng cử chỉ tay

## 1. Mục tiêu bài tập

Dùng webcam, OpenCV và MediaPipe để nhận diện 6 cử chỉ tay, truyền kết quả qua ROS 2 và điều khiển TurtleBot 4 trong Gazebo. Robot chỉ chạy sau khi xác nhận; hỗ trợ tạm dừng, tiếp tục và hủy hành động.

Luồng xử lý: **Webcam → nhận diện → `/detected_gesture` → điều khiển hành vi → `/cmd_vel`**.

## 2. Cấu trúc thư mục

```text
b6/
├── README.md
├── b6_env.bash                 # Nạp ROS 2, môi trường lec4 và overlay B6
├── requirements.txt
└── src/b6_gesture_control/
    ├── package.xml, setup.py, setup.cfg
    ├── resource/b6_gesture_control
    ├── launch/gesture_demo.launch.py
    ├── b6_gesture_control/
    │   ├── gesture_recognition_node.py
    │   └── robot_behavior_node.py
    └── test/test_behavior_transitions.py
```

## 3. Cài đặt và chuẩn bị môi trường

Cần Ubuntu 22.04, ROS 2 Humble, Python 3.10, TurtleBot 4 Simulation/Gazebo Fortress và webcam. Workspace `~/HRI/lec4` phải được build từ bài trước và có package `lec4_robot_lab`; B6 dùng lại world `lec4_small_room` và robot `lite`.

Mã trên GitHub nằm ngay tại thư mục gốc nhánh `assignments_6`. Nếu chưa có thư mục B6:

```bash
git clone --single-branch --branch assignments_6 https://github.com/kieudung12/HRI_k68e-re.git ~/HRI/b6
```

### 3.1. Cài đặt các gói phụ thuộc

```bash
cd ~/HRI/b6
source ../lec4/lab_env.bash
python3 -m pip install --user -r requirements.txt
```

Lần đầu chạy cần Internet để tải model vào `~/.cache/b6_gesture_control/`. Webcam cần quyền truy cập `/dev/video*` và phiên desktop để mở cửa sổ OpenCV.

Tham khảo: [MediaPipe Gesture Recognizer](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer), [TurtleBot 4](https://turtlebot.github.io/turtlebot4-user-manual/).

### 3.2. Thiết lập môi trường và Build Package

```bash
cd ~/HRI/b6
source ../lec4/lab_env.bash
colcon build --packages-select b6_gesture_control --symlink-install
source ./b6_env.bash
```

Mỗi terminal mới phải source `./b6_env.bash` trước khi chạy lệnh ROS. Sau khi sửa mã, build và khởi động lại launch.

## 4. Hướng dẫn chạy từng phần

### 4.1. Chạy mô phỏng và webcam

```bash
cd ~/HRI/b6
source ./b6_env.bash
ros2 launch b6_gesture_control gesture_demo.launch.py
```

Launch mở Gazebo và hai node nhận diện/điều khiển. Webcam hiển thị cử chỉ, confidence, frame ổn định và trạng thái robot. Có thể đổi camera hoặc giảm debounce:

```bash
ros2 launch b6_gesture_control gesture_demo.launch.py camera:=1 stable_frames:=2
```

Mặc định: camera `0`, debounce cử chỉ tĩnh `3` frame, confidence tối thiểu `0.60`. Wave là cử chỉ động suy ra từ landmark: mở bàn tay, lắc ngang có đổi hướng; sau khi phát hiện cần `2` frame để xác nhận. Khi robot đang chạy/tạm dừng, Open Palm luôn được ưu tiên làm lệnh tạm dừng.

### 4.2. Chọn, xác nhận và điều khiển hành động

| Cử chỉ | Nhãn ROS | Tác dụng |
| --- | --- | --- |
| Giơ 1 ngón | `Pointing_Up` | Chọn tiến–lùi 4 chu kỳ |
| Giơ 2 ngón | `Victory` | Chọn chạy tròn liên tục |
| Vẫy tay | `Wave` | Chọn xoay trái–phải chào |
| Giơ ngón cái | `Thumb_Up` | Xác nhận hoặc tiếp tục hành động tạm dừng |
| Xòe bàn tay | `Open_Palm` | Tạm dừng, giữ tiến độ |
| Nắm tay | `Closed_Fist` | Hủy hành động/lựa chọn, về chờ |

1. Chọn hành động; đợi `SELECTED`, rồi giơ ngón cái để chạy (`RUNNING`).
2. Xòe tay để tạm dừng (`PAUSED`); giơ ngón cái để chạy nốt phần còn lại. Thời gian tạm dừng không tính vào tiến độ.
3. Nắm tay để hủy và về `WAITING`. Muốn chọn hành động khác khi đang chạy/tạm dừng thì hủy trước.
4. Tiến–lùi và chào tự kết thúc ở `COMPLETED`; muốn chạy lại phải chọn và xác nhận lại. Chạy tròn tiếp tục đến khi tạm dừng hoặc hủy.

Open Palm lúc đang chờ xác nhận giữ nguyên lựa chọn. Tiến–lùi khoảng 27 cm mỗi chiều; greeting xoay tại chỗ trong khoảng 3.1 giây. Chuyển động dùng vận tốc/thời gian, không hiệu chỉnh theo odometry; giữ vùng trống quanh robot và không chạy teleop cùng lúc.

Mất heartbeat quá `0.8` giây sẽ tạm dừng và giữ tiến độ. Sau khi khôi phục tín hiệu, **xòe bàn tay rồi giơ ngón cái** để tiếp tục; giữ sẵn ngón cái không làm robot tự chạy lại. Không thấy tay nhưng camera còn gửi `NONE` thì hành động đã xác nhận vẫn tiếp tục.

### 4.3. Kiểm tra và quay video demo

Trong terminal đã source môi trường, xem trạng thái hoặc vận tốc (mỗi lệnh echo chạy ở một terminal riêng):

```bash
ros2 topic echo /robot_behavior_state
ros2 topic echo /cmd_vel
```

`/detected_gesture` và `/robot_behavior_state` dùng `std_msgs/msg/String`; `/cmd_vel` dùng `geometry_msgs/msg/Twist`.

Quay Gazebo cạnh webcam, phóng to robot. Trình tự ngắn: **chọn tiến–lùi → xác nhận → tạm dừng → tiếp tục → hoàn tất; chọn chạy tròn → xác nhận → nắm tay hủy; chọn Wave → xác nhận → chào**. Đợi trạng thái trên webcam đổi trước mỗi bước, không dùng bàn phím điều khiển robot.

Kiểm thử logic không cần webcam/Gazebo:

```bash
python3 -m unittest discover -s src/b6_gesture_control/test -v
```

Kiểm thử này không thay thế quan sát nhận diện và chuyển động thực tế. `Ctrl+C` đóng launch; `Q` hoặc `Esc` đóng node webcam, sau đó watchdog tạm dừng robot.

## 5. Khắc phục sự cố thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không tìm thấy `b6_gesture_control` | Build ở `~/HRI/b6`, source `./b6_env.bash`; kiểm tra bằng `ros2 pkg prefix b6_gesture_control`. |
| Không tìm thấy `lec4_robot_lab` | Đặt workspace `lec4` cạnh `b6`, build `lec4` trước và source lại môi trường. |
| Không mở được webcam | Kiểm tra `ls /dev/video*`, đóng ứng dụng khác đang dùng camera; thử `camera:=1`. |
| `NO HAND` hoặc không nhận Wave | Đưa toàn bộ bàn tay vào khung hình, đủ sáng; vẫy ngang có đổi hướng rồi đợi `SELECTED`. |
| Ngón cái không làm robot chạy | Cần chọn trước khi xác nhận. Nếu báo `SIGNAL LOST`, khôi phục camera rồi xòe tay và giơ ngón cái lại. |
| `RUNNING` nhưng robot đứng yên | Kiểm tra Gazebo không bị pause, `ros2 topic info /cmd_vel --verbose` có subscriber; tắt node khác cùng publish vận tốc. |
| Muốn chọn hành động khác khi đang tạm dừng | Nắm tay để hủy, sau đó chọn và xác nhận hành động mới. |
