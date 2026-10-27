# Bài thực hành 06 — TurtleBot 4 điều khiển bằng cử chỉ tay

## 1. Mục tiêu bài tập

Workspace B6 dùng lại world và launch mô phỏng trong `../lec4`. Webcam laptop cung cấp ảnh cho OpenCV và MediaPipe Gesture Recognizer; node `gesture_recognition_node` nhận diện cử chỉ và publish `/detected_gesture`. Node `robot_behavior_node` chờ xác nhận bằng ngón cái rồi điều khiển TurtleBot 4 qua `/cmd_vel` trong Gazebo.

Mã B6 trên nhánh `assignments_6` nằm trong thư mục `b6/`. Khi lấy mã về máy, đặt workspace này tại `~/HRI/b6`, cạnh workspace mô phỏng `~/HRI/lec4` đã build từ bài trước.

- Đọc webcam và nhận diện tối thiểu 5 cử chỉ tay bằng OpenCV và MediaPipe.
- Truyền kết quả nhận diện giữa các node ROS 2 để chọn và xác nhận hành vi robot.
- Điều khiển tiến–lùi, chạy tròn và xoay chào; hỗ trợ tạm dừng, tiếp tục, hủy và dừng khi mất heartbeat.

## 2. Cấu trúc thư mục

```text
b6/
├── README.md
├── b6_env.bash
├── requirements.txt
└── src/b6_gesture_control/
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/b6_gesture_control
    ├── launch/gesture_demo.launch.py
    ├── b6_gesture_control/
    │   ├── gesture_recognition_node.py
    │   └── robot_behavior_node.py
    └── test/test_behavior_transitions.py
```

## 3. Cài đặt và chuẩn bị môi trường

Máy cần Ubuntu 22.04, ROS 2 Humble, TurtleBot 4 Simulation/Gazebo Fortress, Python 3.10, webcam và workspace `lec4` đã build theo hướng dẫn trong `../lec4/README.md`. Launch B6 gọi package `lec4_robot_lab`, dùng robot `lite` và world mặc định `lec4_small_room`. Hai workspace cần nằm cạnh nhau tại `~/HRI/b6` và `~/HRI/lec4`.

### 3.1. Cài đặt các gói phụ thuộc

Cài các thư viện Python theo phiên bản trong `requirements.txt`:

```bash
cd ~/HRI/b6
source ../lec4/lab_env.bash
python3 -m pip install --user -r requirements.txt
```

Các phiên bản sử dụng: NumPy `1.26.4`, OpenCV `4.10.0.84`, MediaPipe `0.10.21`. Lần đầu chạy cần Internet để tải `gesture_recognizer.task`; model được lưu tại `~/.cache/b6_gesture_control/gesture_recognizer.task`. Những lần sau dùng lại model đã tải. Webcam cần được hệ điều hành nhận tại `/dev/video*`; cửa sổ OpenCV cần phiên desktop có GUI.

**Tài liệu tham khảo:**

- [MediaPipe Gesture Recognizer](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer) — nhận diện tư thế tay và landmark.
- [OpenCV](https://docs.opencv.org/4.x/) — đọc webcam và hiển thị ảnh.
- [TurtleBot 4 User Manual](https://turtlebot.github.io/turtlebot4-user-manual/) — robot và mô phỏng.
- [IntellisenseLab QBot](https://github.com/IntellisenseLab/final-project-theflysky) — tham khảo tổ chức node nhận diện cử chỉ và điều khiển ROS 2.
- [VirtuHand](https://github.com/Srecharan/VirtuHand) — tham khảo xử lý chuỗi landmark cho cử chỉ động.

### 3.2. Thiết lập môi trường và Build Package

Build trong workspace B6, sau đó source overlay:

```bash
cd ~/HRI/b6
source ../lec4/lab_env.bash
colcon build --packages-select b6_gesture_control --symlink-install
source ./b6_env.bash
ros2 pkg prefix b6_gesture_control
```

Lệnh cuối phải in đường dẫn dạng `~/HRI/b6/install/b6_gesture_control`. File `b6_env.bash` nạp môi trường mô phỏng từ `lec4`, overlay B6 và đặt log trong `b6/log/ros`. Mỗi terminal mới đều cần source lại file này trước khi chạy lệnh ROS.

## 4. Hướng dẫn chạy từng phần

Mỗi terminal chạy lệnh ROS của B6 cần nạp môi trường bằng `cd ~/HRI/b6 && source ./b6_env.bash`.

### 4.1. Chạy demo gộp — Gazebo và hai node cử chỉ

```bash
cd ~/HRI/b6
source ./b6_env.bash
ros2 launch b6_gesture_control gesture_demo.launch.py
```

Cửa sổ webcam hiển thị 21 landmark, tên cử chỉ, confidence, số frame ổn định, FPS và trạng thái robot. Đưa toàn bộ bàn tay vào khung ảnh; `NO HAND` nghĩa là hiện chưa phát hiện tay.

Có thể đổi camera, giảm số frame debounce hoặc tắt cửa sổ Gazebo:

```bash
ros2 launch b6_gesture_control gesture_demo.launch.py camera:=1 stable_frames:=2 gui:=false
```

`gui:=false` chỉ tắt GUI Gazebo; webcam vẫn mở. Mặc định: `camera:=0`, `stable_frames:=3`, `gui:=true`, `world:=lec4_small_room`.

### 4.2. Chạy riêng từng node

Mỗi terminal đều source `b6_env.bash` trước. Chọn cách chạy tách hoặc demo gộp, tránh mở trùng các node.

Terminal 1 — Gazebo:

```bash
ros2 launch lec4_robot_lab sim.launch.py model:=lite gui:=true rviz:=false
```

Terminal 2 — điều khiển hành vi:

```bash
ros2 run b6_gesture_control robot_behavior_node
```

Terminal 3 — webcam và nhận diện:

```bash
ros2 run b6_gesture_control gesture_recognition_node --ros-args -p camera_index:=0 -p stable_frames:=3 -p min_confidence:=0.60 -p display:=true
```

Không dùng teleop, các nút điều khiển vận tốc hoặc node khác cùng publish `/cmd_vel` trong lúc demo. Dùng vùng trống quanh robot để tiến–lùi và chạy tròn. `Ctrl+C` kết thúc launch; `Q` hoặc `Esc` trong cửa sổ webcam đóng node nhận diện, sau đó watchdog tạm dừng robot khi mất heartbeat.

### 4.3. Nhận diện cử chỉ và chống nhiễu

Model MediaPipe mặc định có các nhãn tư thế tay tĩnh nhưng không có Wave. B6 nhận Wave từ chuỗi landmark bàn tay mở chuyển động ngang và đổi hướng. Cử chỉ tĩnh cần 3 frame liên tiếp, confidence ít nhất 0.60. Wave cần ít nhất 4 mẫu trong cửa sổ 1 giây, một lần đổi hướng và biên độ khoảng 18% bề rộng lòng bàn tay trong ảnh, tối thiểu 0.018 chiều rộng ảnh; sau đó xác nhận qua 2 frame.

Khi chọn Wave, node phân biệt chuyển động ngang với bàn tay mở đứng yên và giữ nhãn trong lúc chuyển sang ngón cái. Node hành vi cũng giữ lựa chọn nếu nhận Open Palm ở cuối động tác vẫy. Khi đang chạy hoặc tạm dừng, Open Palm được ưu tiên để lệnh tạm dừng không bị nhận thành Wave.

Nhãn ổn định được publish liên tục như heartbeat; node điều khiển chỉ xử lý khi nhãn thay đổi, nên giữ nguyên một cử chỉ không kích hoạt hành vi nhiều lần. Camera vẫn hoạt động nhưng không thấy tay hoặc confidence thấp sẽ gửi `NONE`; hành vi đã xác nhận tiếp tục. Mất heartbeat quá 0.8 giây sẽ tạm dừng và giữ tiến độ; cần Thumbs Up để tiếp tục khi tín hiệu trở lại. Thời gian tạm dừng không tính vào tiến độ hành vi.

### 4.4. Chọn, xác nhận và điều khiển hành vi robot

| Cử chỉ | Nhãn `/detected_gesture` | Hành vi |
| --- | --- | --- |
| Giơ một ngón tay | `Pointing_Up` | Chọn tiến–lùi 4 chu kỳ |
| Giơ hai ngón tay | `Victory` | Chọn di chuyển theo quỹ đạo tròn |
| Vẫy tay trái–phải | `Wave` | Chọn xoay trái–phải để chào |
| Giơ ngón cái | `Thumb_Up` | Xác nhận hành vi đã chọn hoặc tiếp tục hành vi tạm dừng |
| Xòe lòng bàn tay | `Open_Palm` | Tạm dừng ngay, giữ tiến độ và phần chuyển động còn lại |
| Nắm tay | `Closed_Fist` | Hủy hành vi/lựa chọn, xóa tiến độ và về `WAITING` |

Robot chỉ bắt đầu chuyển động sau khi xác nhận bằng ngón cái. Trình tự demo:

1. Chọn bằng Pointing Up, Victory hoặc Wave; chờ `SELECTED | ...` xuất hiện trên webcam.
2. Giơ ngón cái đến khi trạng thái đổi sang `RUNNING | ...`.
3. Xòe bàn tay để tạm dừng: robot phát vận tốc 0 và báo `PAUSED | ...`.
4. Giơ ngón cái để chạy tiếp đúng đoạn còn lại. Ví dụ đoạn tiến dài 1.5 giây đã chạy 0.5 giây thì sau khi tiếp tục chỉ chạy nốt 1.0 giây.
5. Nắm tay để hủy và về `WAITING | SELECT AN ACTION`. Khi đang chạy/tạm dừng, phải hủy trước nếu muốn chọn hành vi khác.

Open Palm khi đang chờ xác nhận giữ nguyên lựa chọn. Khi hành vi hữu hạn hoàn tất, robot dừng và báo `COMPLETED | ...`; giơ ngón cái đơn lẻ không chạy lại hành vi đã hoàn tất.

Tiến–lùi dùng 0.18 m/s trong 1.5 giây mỗi chiều, khoảng 27 cm mỗi lượt, nghỉ 0.3 giây khi đổi chiều và lặp 4 chu kỳ. Đường tròn dùng 0.12 m/s và 0.32 rad/s, bán kính danh định khoảng 0.375 m; lặp liên tục đến khi tạm dừng hoặc hủy. Greeting xoay trái, phải, rồi trở về hướng ban đầu; tổng chương trình khoảng 3.1 giây, chưa tính thời gian tạm dừng. Khoảng cách/góc được tính theo vận tốc và thời gian lệnh, không có hiệu chỉnh bằng odometry.

### 4.5. Theo dõi các topic ROS 2

Sau khi simulator và hai node khởi động, mở terminal đã source môi trường B6:

```bash
ros2 topic info /detected_gesture
ros2 topic info /cmd_vel
ros2 topic echo /robot_behavior_state
```

`/cmd_vel` cần có publisher từ node hành vi và subscriber của mô phỏng.

| Topic | Kiểu message | Nội dung |
| --- | --- | --- |
| `/detected_gesture` | `std_msgs/msg/String` | Nhãn cử chỉ ổn định hoặc `NONE` |
| `/robot_behavior_state` | `std_msgs/msg/String` | `WAITING`, `SELECTED`, `RUNNING`, `PAUSED`, `COMPLETED` |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Vận tốc tiến và xoay |

Có thể quan sát từng luồng ở các terminal riêng:

```bash
ros2 topic echo /detected_gesture
```

```bash
ros2 topic echo /cmd_vel
```

### 4.6. Kiểm tra logic không cần ROS/Gazebo

```bash
cd ~/HRI/b6
python3 -m unittest discover -s src/b6_gesture_control/test -v
```

Bộ kiểm tra dùng đồng hồ và publisher giả, gồm 10 test cho tạm dừng/tiếp tục từng hành vi, nhiều lần dừng, giữ đoạn chuyển động còn lại, hủy bằng nắm tay, mất heartbeat, hoàn tất và ưu tiên Open Palm. Các test đã đạt và package đã build thành công trong workspace phát triển; kiểm tra này chưa thay thế kiểm tra webcam và chuyển động thực tế trong Gazebo.

## 5. Khắc phục sự cố thường gặp

### 5.1. Không tìm thấy package B6

Nếu gặp `Package 'b6_gesture_control' not found`, nạp lại overlay trong đúng terminal:

```bash
cd ~/HRI/b6
source ./b6_env.bash
ros2 pkg prefix b6_gesture_control
```

Lệnh cuối phải in đường dẫn dạng `~/HRI/b6/install/b6_gesture_control`. Nếu vẫn chưa thấy package, thực hiện lại bước build rồi source lại. Không chạy colcon từ `~` hoặc workspace khác.

### 5.2. Lỗi webcam, nhận diện và điều khiển

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không tìm thấy `lec4_robot_lab` hoặc world | Đặt `lec4` cạnh `b6`, build workspace `lec4` trước rồi source `../lec4/lab_env.bash` và `./b6_env.bash`. |
| `Cannot open webcam index` | Kiểm tra `ls /dev/video*`, đóng ứng dụng đang dùng camera; thử `camera:=1` khi launch hoặc `-p camera_index:=1` khi chạy node riêng. |
| Cửa sổ báo `NO HAND` hoặc confidence thấp | Đưa toàn bộ bàn tay vào khung ảnh, hướng lòng bàn tay về camera và bảo đảm đủ sáng. Kiểm tra camera đang chọn đúng thiết bị. |
| Wave bị hiển thị thành Open Palm | Xòe bàn tay và lắc ngang trái–phải có đổi hướng; chờ `SELECTED` trước khi giơ ngón cái. Wave chỉ dùng để chọn khi robot chưa chạy; khi đang chạy/tạm dừng, Open Palm là lệnh tạm dừng. |
| Giơ ngón cái nhưng vẫn `WAITING` | Chưa có hành vi được chọn. Chọn Pointing Up, Victory hoặc Wave; đợi `SELECTED`, sau đó giơ ngón cái để xác nhận. |
| `RUNNING` nhưng robot không chuyển động | Xem `ros2 topic echo /cmd_vel` và `ros2 topic info /cmd_vel --verbose`; cần có subscriber của mô phỏng. Đóng teleop hoặc node khác phát vận tốc 0, kiểm tra Gazebo đang chạy và không bị pause. |
| Robot báo `PAUSED` | Open Palm hoặc mất heartbeat đã tạm dừng hành vi. Khôi phục tín hiệu rồi giơ ngón cái để tiếp tục; nắm tay để hủy và về chờ. |
| Sau khi hoàn tất, giơ ngón cái không chạy lại | `COMPLETED` nghĩa là hành vi cũ đã kết thúc. Chọn hành vi mới rồi xác nhận lại. |
| Nhận diện phản hồi chậm | Thử `stable_frames:=2` khi launch; theo dõi FPS và số frame ổn định trên webcam. Giảm debounce cũng làm hệ thống nhạy hơn với nhiễu. |
| Đã sửa code nhưng node vẫn chạy như cũ | Dừng launch, build lại từ `~/HRI/b6`, source `./b6_env.bash` rồi khởi động lại demo. |
