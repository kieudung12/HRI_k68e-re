# Bài thực hành 04 — TurtleBot 4, SLAM và Nav2

> Workspace ROS 2 cho mô phỏng TurtleBot 4 trong Gazebo Fortress, xây dựng bản đồ bằng SLAM Toolbox, định vị với AMCL và điều hướng bằng Nav2.

## 1. Mục tiêu

- Khởi chạy TurtleBot 4 trong world `lec4_small_room`.
- Kiểm tra các luồng dữ liệu cảm biến và odometry trong mô phỏng.
- Tạo, lưu và sử dụng bản đồ 2D dưới dạng `map.yaml` và `map.pgm`.
- Định vị robot trên bản đồ và gửi mục tiêu điều hướng bằng RViz2.

## 2. Cấu trúc dự án

```text
lec4/
├── README.md
├── lab_env.bash                    # Nạp ROS và thiết lập môi trường riêng cho lab
└── src/lec4_robot_lab/
    ├── CMakeLists.txt
    ├── package.xml
    ├── config/                     # Tham số SLAM, AMCL, Nav2 và cấu hình giao diện
    ├── launch/                     # Launch mô phỏng, SLAM, localization và Nav2
    ├── maps/
    │   ├── map.yaml
    │   └── map.pgm
    ├── scripts/                    # Teleop và các tiện ích cho runtime
    └── worlds/
        └── lec4_small_room.sdf
```

Các launch file chính:

| Launch file | Chức năng |
| --- | --- |
| `sim.launch.py` | Khởi chạy Gazebo và TurtleBot 4 |
| `slam.launch.py` | Chạy SLAM Toolbox và RViz2 để tạo bản đồ |
| `nav.launch.py` | Chạy localization; tùy chọn khởi động Nav2 |
| `view.launch.py` | Mở RViz2 với cấu hình của package |

## 3. Yêu cầu

- Ubuntu 22.04 LTS
- ROS 2 Humble
- Gazebo Fortress và các package TurtleBot 4 cho ROS 2 Humble
- `colcon` và `rosdep`

Cài công cụ build và cài các dependency được khai báo trong `package.xml`:

```bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep

# Chỉ chạy rosdep init nếu máy chưa khởi tạo rosdep.
sudo rosdep init
rosdep update

cd ~/HRI/lec4
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

## 4. Build workspace

```bash
cd ~/HRI/lec4
source /opt/ros/humble/setup.bash
bash setup_runtime.sh
source ./lab_env.bash
colcon build --packages-select lec4_robot_lab --symlink-install
source install/setup.bash
```

Trong **mỗi terminal mới**, nạp môi trường trước khi chạy ROS:

```bash
cd ~/HRI/lec4
source ./lab_env.bash
```

`lab_env.bash` thiết lập ROS domain và Gazebo partition riêng cho bài thực hành. Nếu clone repo vào vị trí khác, thay `~/HRI/lec4` bằng đường dẫn workspace của bạn.

`setup_runtime.sh` build thư viện `tf2_ros 0.25.22` chính thức tại `.runtime/` để tương thích với Nav2 Humble trên máy này. `lab_env.bash` nạp thư viện đó cùng cấu hình DDS UDP cho các terminal. Thư viện ROS hệ thống không bị ghi đè; cần chạy setup một lần khi checkout sang máy mới.

## 5. Chạy mô phỏng và SLAM

Mở các terminal riêng và nạp `lab_env.bash` trong từng terminal.

**Terminal 1 — khởi chạy mô phỏng:**

```bash
ros2 launch lec4_robot_lab sim.launch.py model:=lite gui:=true rviz:=false
```

Robot xuất hiện ngay tại tâm phòng `(x=0, y=0)`, hướng `+X`, không có dock và không chạy undock. Chờ `/scan` và `/odom` có dữ liệu trước khi mở SLAM.

**Terminal 2 — chạy SLAM và RViz2:**

```bash
ros2 launch lec4_robot_lab slam.launch.py
```

**Terminal 3 — điều khiển robot bằng bàn phím:**

```bash
ros2 run lec4_robot_lab drive_wasd.py
```

Di chuyển robot để khảo sát môi trường và quan sát bản đồ trong RViz2. Khi bản đồ đã đủ rõ, thoát teleop nhưng để SLAM tiếp tục chạy. Lưu bản đồ từ một terminal đã nạp môi trường:

```bash
ros2 topic info /map
ros2 run nav2_map_server map_saver_cli \
  -f "$LEC4_WS/src/lec4_robot_lab/maps/map"
```

Lệnh tạo cặp file `src/lec4_robot_lab/maps/map.yaml` và `map.pgm`. Giữ hai file cùng thư mục vì YAML tham chiếu ảnh bản đồ bằng đường dẫn tương đối.

## 6. Localization và điều hướng Nav2

Trước tiên dừng SLAM và Gazebo bằng `Ctrl+C`, sau đó khởi động lại mô phỏng ở **Terminal 1**:

```bash
ros2 launch lec4_robot_lab sim.launch.py model:=lite gui:=true rviz:=false
```

Robot đứng yên tại tâm phòng; không cần gửi lệnh undock. Trong **Terminal 2**, chạy localization, Nav2 và RViz2:

```bash
ros2 launch lec4_robot_lab nav.launch.py nav2:=true rviz:=true \
  map:="$LEC4_WS/src/lec4_robot_lab/maps/map.yaml"
```

Trong RViz2:

1. Chọn **2D Pose Estimate**, đặt vị trí và hướng ban đầu tương ứng với robot trong Gazebo.
2. Đợi laser scan khớp với tường trên bản đồ; panel **Navigation 2** phải báo Localization và Navigation `active`.
3. Chọn **Nav2 Goal**, click giữ ở vùng trống, kéo mũi tên rồi thả. Panel sẽ hiển thị trạng thái goal và nút Cancel khi goal được nhận. Robot chỉ tự di chuyển sau bước này.

Giữ panel **Navigation 2** trong RViz. GoalTool của Nav2 Humble gửi goal thông qua panel này; xóa panel sẽ khiến kéo Nav2 Goal không gửi action dù các server đều `active`.

Chỉ chạy một stack localization/Nav2 cho mỗi phiên mô phỏng. Dừng Nav2 trước Gazebo khi kết thúc; khi khởi động lại, đợi các tiến trình cũ thoát hoàn toàn để tránh dùng lại dữ liệu TF của phiên trước.

## 7. Cấu hình bản đồ

Thông tin bản đồ được khai báo trong [`src/lec4_robot_lab/maps/map.yaml`](src/lec4_robot_lab/maps/map.yaml); dữ liệu ảnh nằm trong [`src/lec4_robot_lab/maps/map.pgm`](src/lec4_robot_lab/maps/map.pgm). Các tham số SLAM, AMCL, Nav2 và RViz2 nằm trong thư mục `src/lec4_robot_lab/config/`.

## 8. Khắc phục sự cố

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Không thấy topic ROS của mô phỏng | Xác nhận đã chạy `source ./lab_env.bash` trong terminal hiện tại và Gazebo đang chạy. |
| Không lưu được bản đồ | Kiểm tra SLAM còn chạy và `/map` có publisher; sau đó chạy lại `map_saver_cli`. |
| Nav2 chưa bắt đầu điều hướng | Xác nhận panel **Navigation 2** có mặt, đặt **2D Pose Estimate**, chờ trạng thái `active` rồi gửi **Nav2 Goal**. |
| Launch báo còn stack cũ | Dừng các launch đang chạy bằng `Ctrl+C`; chỉ mở lại sau khi simulator và stack cũ đã thoát. |

Nếu terminal cũ đã đóng, dừng các process group của launch bài này trước khi chạy lại:

```bash
for pid in $(pgrep -f '^/usr/bin/python3 /opt/ros/humble/bin/ros2 launch lec4_robot_lab '); do
  pgid=$(ps -o pgid= -p "$pid" | tr -d ' ')
  [ -z "$pgid" ] || kill -INT -- "-$pgid"
done
sleep 5
```
