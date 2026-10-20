# TurtleBot 4 Autonomous Navigation and YOLO

ROS 2 Humble workspace cho bài thực hành TurtleBot 4: localization trên bản đồ đã lưu, điều hướng tự động bằng Nav2 qua các goal và nhận diện vật thể từ camera bằng YOLO.

## 1. Giới thiệu

Package `b5_tb4_lab` thực hiện các nội dung:

- Nạp lại bản đồ `map.yaml` và `map.pgm` đã xây dựng trong bài thực hành tuần trước.
- Khởi chạy TurtleBot 4 trong Gazebo, định vị bằng AMCL và lập kế hoạch bằng Nav2.
- Chạy node Python gửi tuần tự ít nhất ba goal trong hệ tọa độ `map`.
- Nhận ảnh RGB, chuyển đổi qua `cv_bridge`, chạy YOLO và hiển thị kết quả có bounding box, tên class, confidence trên cửa sổ OpenCV; đồng thời publish ảnh đã annotate và log detection ra terminal.

> [!IMPORTANT]
> **B5 phụ thuộc vào workspace `lec4` của bài thực hành tuần trước và không chạy độc lập nếu thiếu workspace đó.** Launch B5 gọi package `lec4_robot_lab` để tái sử dụng mô phỏng, world, runtime, localization và Nav2; `b5_env.bash` cũng source `../lec4/lab_env.bash`. Hãy lấy workspace `lec4` đầy đủ từ lớp, đặt cạnh thư mục `b5` (ví dụ `~/HRI/lec4` và `~/HRI/b5`) và build `lec4` trước B5. Workspace `lec4` không được chứa trong repository/ZIP B5 này.

## 2. Cấu trúc thư mục

```text
~/HRI/
├── lec4/                              # Workspace bài trước, cần được cung cấp riêng
│   ├── lab_env.bash
│   ├── setup_runtime.sh
│   └── src/lec4_robot_lab/
└── b5/
    ├── README.md
    ├── process.md                    # Nhật ký phiên làm việc và xử lý lỗi
    ├── b5_env.bash                   # Nạp runtime lec4, sau đó overlay B5
    ├── evidence/
    │   └── yolo_chair_detection.jpg
    └── src/b5_tb4_lab/
        ├── launch/                   # Wrapper gọi launch từ lec4
        ├── maps/map.{yaml,pgm}       # Bản đồ được sao chép từ lec4
        ├── config/goals.yaml         # Danh sách goal trong frame map
        ├── worlds/chair_target.sdf   # Ghế mô phỏng cho demo YOLO
        └── b5_tb4_lab/
            └── autonomous_yolo.py   # Node điều hướng và nhận diện
```

## 3. Cài đặt và chuẩn bị môi trường

### 3.1. Yêu cầu hệ thống

- Ubuntu 22.04 LTS và ROS 2 Humble.
- TurtleBot 4 Simulation, Gazebo Fortress, Nav2, RViz2.
- `colcon`, `rosdep`, Python 3.10 và pip.
- Workspace đầy đủ của bài `lec4`, đặt cạnh workspace `b5` như cấu trúc ở mục 2.

Nếu không có `lec4`, lấy workspace này từ bộ bài thực hành tuần trước/lớp học. Chỉ có repository B5 sẽ không đủ để chạy các launch mô phỏng và navigation.

Clone branch B5 vào đúng vị trí trong workspace:

```bash
mkdir -p ~/HRI
git clone --single-branch --branch assignments_5 \
  https://github.com/kieudung12/HRI_k68e-re.git ~/HRI/b5
```

### 3.2. Cài đặt các gói phụ thuộc

Cài công cụ ROS và các dependency của B5:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-humble-turtlebot4-navigation \
  ros-humble-nav2-simple-commander \
  ros-humble-cv-bridge \
  python3-yaml \
  python3-opencv
```

Cài các thư viện Python cho YOLO/OpenCV:

```bash
python3 -m pip install --user \
  'numpy==1.26.4' \
  'opencv-python==4.10.0.84' \
  ultralytics
```

NumPy được ghim ở `1.26.4` để tương thích với `cv_bridge` được build cho ROS Humble. Không nâng NumPy lên 2.x trong Python environment này; có thể gặp lỗi `_ARRAY_API not found` hoặc crash khi chuyển ảnh ROS sang OpenCV.

### 3.3. Thiết lập môi trường và build package

Thực hiện theo thứ tự: cài/build workspace `lec4`, sau đó build B5.

**Cài dependency và build `lec4`** (trên máy mới):

```bash
# Chỉ chạy rosdep init nếu máy chưa khởi tạo rosdep.
sudo rosdep init
rosdep update

cd ~/HRI/lec4
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
bash setup_runtime.sh
source ./lab_env.bash
colcon build --packages-select lec4_robot_lab --symlink-install
source install/setup.bash
```

`setup_runtime.sh` là một phần của workspace `lec4` và cần chạy theo README của bài đó. Nếu `rosdep` đã được khởi tạo trước đây, bỏ qua `sudo rosdep init`.

**Build B5:**

```bash
cd ~/HRI/b5
source ../lec4/lab_env.bash
colcon build --symlink-install
source ./b5_env.bash
ros2 pkg prefix lec4_robot_lab
ros2 pkg prefix b5_tb4_lab
```

Hai lệnh `ros2 pkg prefix` cần tìm thấy cả hai package. Trong mỗi terminal mới dùng cho B5, chạy:

```bash
cd ~/HRI/b5
source ./b5_env.bash
```

Nếu đặt hai workspace ở vị trí khác, thay `~/HRI` bằng đường dẫn tương ứng nhưng giữ `lec4` và `b5` cạnh nhau để đường dẫn tương đối `../lec4` còn đúng.

## 4. Hướng dẫn chạy

Mở ba terminal riêng. Trong mỗi terminal, source môi trường B5 trước khi gọi lệnh ROS. Không source workspace ROS khác đè lên môi trường sau đó.

### 4.1. Khởi chạy Gazebo

**Terminal 1:**

```bash
cd ~/HRI/b5
source ./b5_env.bash
ros2 launch b5_tb4_lab sim.launch.py model:=lite gui:=true rviz:=false
```

Launch dùng world `lec4_small_room` từ package `lec4_robot_lab`. B5 thay landmark hộp phía đông nam bằng mô hình ghế để có đối tượng COCO cho demo YOLO. Đợi robot xuất hiện và các topic cảm biến hoạt động.

### 4.2. Nạp bản đồ và khởi chạy AMCL/Nav2

**Terminal 2:**

```bash
cd ~/HRI/b5
source ./b5_env.bash
ros2 launch b5_tb4_lab navigation.launch.py
```

Launch nạp map mặc định `b5_tb4_lab/maps/map.yaml` và gọi localization/Nav2/RViz từ `lec4_robot_lab`. Map B5 gồm cặp `map.yaml` và `map.pgm` được sao chép từ bài trước.

### 4.3. Đặt Initial Pose trên RViz2

Trong RViz2:

1. Đặt **Fixed Frame** là `map`.
2. Chọn **2D Pose Estimate**, đặt tâm và hướng robot khớp với vị trí thực tế trong Gazebo (robot bắt đầu gần `(0, 0)`, yaw `0`).
3. Chờ scan LiDAR khớp với tường trên bản đồ và localization/Nav2 chuyển sang trạng thái active.

Nếu scan lệch lâu khi robot đứng yên, đặt lại pose và xác nhận đang dùng đúng map/world. Khi robot di chuyển, các vật cản đã thay đổi so với map (ví dụ ghế thay landmark hộp) có thể tạo sai khác cục bộ. Chỉ chạy một simulator và một stack localization/Nav2.

### 4.4. Chạy node điều hướng và YOLO

**Terminal 3:**

```bash
cd ~/HRI/b5
source ./b5_env.bash
ros2 run b5_tb4_lab autonomous_yolo --ros-args -p image_topic:=/oakd/rgb/preview/image_raw -p display:=true
```

Node chờ AMCL/Nav2 sẵn sàng, sau đó gửi các goal trong `config/goals.yaml` tuần tự bằng Nav2 Simple Commander. Đồng thời, node subscribe camera, chuyển ảnh qua `cv_bridge`, chạy YOLO:

- Cửa sổ OpenCV hiện ảnh camera với bounding box, class và confidence.
- Terminal in nhãn/confidence cùng kết quả từng goal.
- Ảnh đã annotate được publish lên `/yolo/detections/image` để xem bằng Image display trên RViz2.

Ảnh preview camera gốc là 320×240; node phóng cửa sổ OpenCV lên 960×720 để dễ quan sát và có thể kéo chỉnh kích thước. Đây là cửa sổ desktop riêng được mở từ terminal 3, không hiển thị ảnh bên trong vùng chữ của terminal. Cần chạy terminal trong phiên desktop có GUI; đưa cửa sổ này vào khung hình OBS khi quay demo.

> Nếu lệnh chỉ có `-p image_topic:=...` mà thiếu `-p display:=true`, node vẫn nhận diện và in log nhưng **không mở cửa sổ camera**.

Không dùng teleop hoặc **Nav2 Goal** trên RViz2 trong khi node tự điều khiển.

Mặc định node dùng model `yolov8n.pt`. Ultralytics tự tải trọng số nếu file chưa có trong workspace; lần chạy đầu cần kết nối Internet. Có thể thử model `yolov8s.pt` để ưu tiên độ chính xác (thường chậm hơn trên CPU); model này cũng được tải khi sử dụng lần đầu:

```bash
ros2 run b5_tb4_lab autonomous_yolo --ros-args \
  -p image_topic:=/oakd/rgb/preview/image_raw \
  -p display:=true \
  -p model:=yolov8s.pt \
  -p confidence:=0.20
```

`confidence:=0.20` là ngưỡng lọc detection tối thiểu, không phải confidence do node ép ra. Score tùy model, góc nhìn và hình dạng/kích thước vật thể; ghế SDF và ảnh preview độ phân giải thấp có thể khiến kết quả dao động hoặc không xuất hiện ở mọi frame.

**Quay video nộp bài:** trước khi chạy node, bắt đầu quay màn hình bằng OBS hoặc công cụ tương tự. Sắp xếp cửa sổ để video thấy Gazebo, map/localization trên RViz2, cửa sổ camera YOLO và terminal có log goal. Dừng quay sau khi terminal báo `Goal 3 reached successfully`; lưu video MP4/MKV. Ghế mục tiêu nằm gần Goal 3 nên detection có thể rõ nhất ở khu vực đó.

## 5. Cấu hình goal

Các goal trong `src/b5_tb4_lab/config/goals.yaml` hiện là tọa độ mẫu được kế thừa từ những lần điều hướng thành công trong `lec4`:

| Goal | x (m) | y (m) | yaw (rad) |
| --- | ---: | ---: | ---: |
| Goal 1 | -1.00 | 1.10 | 0.29 |
| Goal 2 | 1.01 | 1.07 | 0.28 |
| Goal 3 | 1.02 | -1.07 | -0.34 |

Các số này chưa phải kết quả đo mới cho bài B5. Để khảo sát goal theo yêu cầu, dùng **Publish Point** trên RViz2 và đọc:

```bash
ros2 topic echo /clicked_point
```

Pose/hướng hiện tại của robot có thể xem bằng:

```bash
ros2 topic echo /amcl_pose
```

Nếu thay bản đồ hoặc vị trí spawn, khảo sát lại các điểm trong frame `map`, kiểm tra chúng nằm trong vùng đi được rồi cập nhật `goals.yaml`.

## 6. Node, topic và action chính

| Thành phần | Tên | Vai trò |
| --- | --- | --- |
| Node điều hướng và nhận diện | `autonomous_yolo` / `b5_yolo_camera` | Gửi các goal tuần tự; subscribe ảnh; chạy YOLO; hiển thị, publish và log kết quả. |
| Action Nav2 | `/navigate_to_pose` | Nhận từng mục tiêu pose trong frame `map` từ Nav2 Simple Commander. |
| Bản đồ | `/map` | Occupancy grid được nạp từ `map.yaml`. |
| LiDAR đầu vào | `/scan` | LaserScan thô từ mô phỏng. |
| LiDAR cho localization/Nav2 | `/scan_amcl` | Scan được throttle từ `/scan` xuống khoảng 10 Hz. |
| Pose AMCL | `/amcl_pose` | Pose ước lượng hiện tại của robot trong map. |
| Initial pose | `/initialpose` (qua relay RViz của `lec4`) | Nhận vị trí khởi tạo localization từ RViz2. |
| Camera RGB | `/oakd/rgb/preview/image_raw` | Ảnh đầu vào mặc định của YOLO. |
| Ảnh YOLO đã annotate | `/yolo/detections/image` | Ảnh camera có bounding box, class và confidence. |
| TF | `map → odom → base_link` | Chuỗi transform localization và odometry dùng để đặt scan/robot trên map. |

Kiểm tra topic camera và scan:

```bash
ros2 topic list | grep -E 'oakd|image|scan'
ros2 topic info /oakd/rgb/preview/image_raw
ros2 topic info /scan_amcl
```

## 7. Khắc phục sự cố thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `Package 'lec4_robot_lab' not found` | Cần workspace bài trước ở `../lec4`; build `lec4_robot_lab` theo mục 3.3 rồi source `b5_env.bash`. B5 không thể chạy hai launch khi thiếu package này. |
| `Package 'b5_tb4_lab' not found` | Trong terminal hiện tại, chạy `cd ~/HRI/b5 && source ./b5_env.bash`; nếu vẫn lỗi, build B5 rồi source lại. |
| `../lec4/lab_env.bash: No such file` | Đặt `lec4` cạnh `b5` theo cấu trúc ở mục 2; xác nhận đường dẫn tương đối `../lec4` tồn tại. |
| `_ARRAY_API not found` hoặc crash tại `cv_bridge` | Dùng NumPy 1.26.4 và OpenCV Python 4.10.0.84 như mục 3.2; không dùng NumPy 2.x với `cv_bridge` apt hiện tại. |
| Cửa sổ camera không hiện | Chạy trong phiên desktop GUI và truyền `-p display:=true`; hoặc xem `/yolo/detections/image` bằng Image display trong RViz2. |
| Camera topic không có publisher | Chạy `ros2 topic list`, tìm topic RGB có tên `oakd` hoặc `image`, rồi truyền bằng `-p image_topic:=...`. |
| LiDAR không khớp tường trên map | Đặt RViz Fixed Frame là `map`, đặt lại **2D Pose Estimate** khi robot đứng yên, xác nhận đúng world/map và không có simulator/Nav2 cũ. Kiểm tra thêm pose/TF/scan bên dưới. |
| Nav2 không gửi goal | Đặt Initial Pose, đợi scan khớp map và lifecycle Nav2 active; chỉ chạy một stack localization/Nav2. |

Lệnh kiểm tra khi LiDAR lệch:

```bash
ros2 topic echo --once /amcl_pose
ros2 run tf2_ros tf2_echo map base_link
ros2 topic hz /scan_amcl
ros2 topic info /scan_amcl
```

AMCL của `lec4` nhận `/scan_amcl` ở khoảng 10 Hz; ngưỡng cập nhật chuyển động tối thiểu hiện là 0,25 m hoặc 0,2 rad. Vật cản thay đổi so với map có thể làm scan lệch cục bộ. Không chỉnh tham số AMCL trước khi xác nhận initial pose, TF, world/map và không có stack trùng.
