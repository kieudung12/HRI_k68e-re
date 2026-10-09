# Bài thực hành 04 — TurtleBot 4, SLAM và Nav2

Toàn bộ file của bài này nằm trong thư mục `b4/`. Không cần tạo ROS package mới.

## Môi trường đã kiểm tra

- Ubuntu 22.04.5
- ROS 2 Humble
- TurtleBot 4 Standard
- World: `maze` (world cục bộ, không phụ thuộc tải model từ Fuel)
- `/scan`, `/odom`, `/cmd_vel` đã được kiểm tra bằng dữ liệu thực
- `slam_toolbox`, `navigation2`, `nav2_bringup` và các package TurtleBot 4 đã có

Các terminal chạy bài này phải là môi trường sạch, chỉ source ROS Humble. Terminal đang source `ros2_ws` có thể làm Gazebo lỗi.

## Terminal sạch

Mở terminal mới và chạy:

```bash
env -i HOME="$HOME" USER="$USER" DISPLAY="$DISPLAY" \
  XAUTHORITY="$XAUTHORITY" XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
  ROS_DOMAIN_ID=30 PATH=/opt/ros/humble/bin:/usr/bin:/bin \
  bash --noprofile --norc
source /opt/ros/humble/setup.bash
cd /home/kieu/HRI/b4
```

Kiểm tra overlay phải chỉ có Humble:

```bash
echo "$AMENT_PREFIX_PATH"
# Kết quả mong đợi: /opt/ros/humble
```

## 1. Chạy simulation

Terminal 1:

```bash
source /opt/ros/humble/setup.bash
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py \
  world:=maze rviz:=false
```

Gazebo phải hiển thị maze và TurtleBot 4. World `warehouse` hiện bị chậm/kẹt do phải tải nhiều model Fuel; dùng `maze` cho toàn bộ bài để mapping và navigation ở cùng một môi trường.

Terminal 2, mở RViz2 bằng cấu hình chính thức:

```bash
source /opt/ros/humble/setup.bash
ros2 run rviz2 rviz2 -d /opt/ros/humble/share/turtlebot4_viz/rviz/robot.rviz
```

Kiểm tra topic:

```bash
ros2 topic info /scan
ros2 topic echo /scan --once
ros2 topic info /odom
ros2 topic echo /odom --once
ros2 topic info /cmd_vel
```

## 2. Chạy SLAM

Terminal 3:

```bash
source /opt/ros/humble/setup.bash
ros2 launch turtlebot4_navigation slam.launch.py \
  use_sim_time:=true sync:=true
```

Kiểm tra:

```bash
ros2 topic info /map
ros2 topic echo /map --once
```

Trong RViz thêm hoặc kiểm tra các display `Map`, `LaserScan`, `RobotModel`, `TF`; đặt Fixed Frame là `map`.

## 3. Teleop và lưu map

Terminal 4:

```bash
source /opt/ros/humble/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Nhấn `i` để chạy tới, `j/l` để xoay, `,` để lùi và `k` để dừng. Khảo sát các hành lang và vật cản chính, đi chậm, tránh va chạm. Khi map đủ rõ, nhấn `Ctrl+C` để dừng teleop nhưng giữ simulation và SLAM.

Tạo thư mục và lưu map:

```bash
mkdir -p /home/kieu/HRI/b4/maps
ros2 run nav2_map_server map_saver_cli \
  -f /home/kieu/HRI/b4/maps/map
```

Kết quả bắt buộc:

```text
/home/kieu/HRI/b4/maps/map.yaml
/home/kieu/HRI/b4/maps/map.pgm
```

Kiểm tra:

```bash
test -s maps/map.yaml && test -s maps/map.pgm
grep '^image:' maps/map.yaml
```

## 4. Localization và Nav2

Dừng SLAM bằng `Ctrl+C`. Giữ nguyên world `maze` và khởi động lại simulation nếu cần.

Localization:

```bash
source /opt/ros/humble/setup.bash
ros2 launch turtlebot4_navigation localization.launch.py \
  use_sim_time:=true \
  map:=/home/kieu/HRI/b4/maps/map.yaml
```

Nav2:

```bash
source /opt/ros/humble/setup.bash
ros2 launch turtlebot4_navigation nav2.launch.py \
  use_sim_time:=true
```

Trong RViz, dùng `2D Pose Estimate`: click vào vị trí thật của robot trên map rồi kéo mũi tên theo hướng robot đang quay. Chờ TF `map -> odom -> base_link` ổn định trước khi gửi goal.

Dùng `Nav2 Goal` để gửi ít nhất hai goal khác nhau. Sau khi gửi goal không chạy teleop; quan sát global path, local path và vận tốc do Nav2 phát hành.

## Ảnh minh chứng

- `01_simulation.png`: Gazebo có maze và TurtleBot 4.
- `02_topics.png`: terminal có kết quả `ros2 topic info/echo` cho `/scan`, `/odom`, `/cmd_vel`.
- `03_lidar_rviz.png`: RViz có RobotModel và LaserScan.
- `04_slam_mapping.png`: RViz đang hiển thị map khi robot được teleop khảo sát.
- `05_saved_map.png`: thư mục `maps/` có `map.yaml` và `map.pgm`.
- `06_localization.png`: map đã lưu và pose robot sau `2D Pose Estimate`.
- `07_nav2_goal_1.png`, `08_nav2_goal_2.png`: hai goal khác nhau và robot tự đi tới.

## Cấu trúc repository để nộp GitHub

```text
b4/
├── b4/__init__.py
├── launch/b4_simulation.launch.py  # wrapper dùng launch chính thức TurtleBot 4
├── maps/map.yaml                   # tạo sau khi mapping
├── maps/map.pgm                    # tạo sau khi mapping
├── package.xml
├── setup.py
├── setup.cfg
└── README.md
```

Build package wrapper từ chính thư mục này:

```bash
cd /home/kieu/HRI/b4
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch b4 b4_simulation.launch.py world:=maze
```

Package này không tự viết simulator, SLAM, localization hoặc Nav2. Nó chỉ cung cấp một launch file của project và gọi các package chính thức đã cài trong ROS 2 Humble. Cấu hình SLAM, localization và Nav2 mặc định được lấy từ `turtlebot4_navigation`.

## Checklist trước khi push repository Public

- [ ] `maps/map.yaml` tồn tại và có kích thước lớn hơn 0.
- [ ] `maps/map.pgm` tồn tại và có kích thước lớn hơn 0.
- [ ] `grep '^image:' maps/map.yaml` trỏ tới `map.pgm`.
- [ ] `colcon build --symlink-install` thành công.
- [ ] Chạy được `ros2 launch b4 b4_simulation.launch.py world:=maze`.
- [ ] README có ảnh minh chứng hoặc đường dẫn tới ảnh báo cáo nếu môn học yêu cầu.
- [ ] Không push `build/`, `install/`, `log/` hoặc file cache.

