# TurtleBot 4 Autonomous Navigation and YOLO

Định vị TurtleBot 4 trên bản đồ có sẵn, điều hướng tuần tự qua ba goal bằng Nav2 và nhận diện vật thể từ camera RGB bằng YOLO trên ROS 2 Humble.

## 1. Giới thiệu

Package `b5_tb4_lab` thực hiện các nội dung của bài thực hành:

- Nạp lại cặp `map.yaml` và `map.pgm` đã xây dựng từ bài trước.
- Khởi chạy TurtleBot 4 trong Gazebo Fortress và định vị bằng AMCL trên RViz2.
- Gửi tuần tự ít nhất ba goal trong hệ tọa độ `map` bằng Nav2 Simple Commander.
- Chuyển ảnh ROS sang OpenCV qua `cv_bridge`, chạy YOLO, vẽ bounding box, tên class và confidence.
- Hiển thị ảnh kết quả trong cửa sổ OpenCV, publish ảnh lên ROS và in nhãn/confidence ra terminal khi phát hiện vật thể.

> [!IMPORTANT]
> **B5 cần workspace `lec4` từ bài thực hành trước.** Hai launch của B5 gọi package `lec4_robot_lab`; script `b5_env.bash` source `../lec4/lab_env.bash`. Repository B5 không chứa workspace `lec4`. Cần clone riêng branch [`assignments_4`](https://github.com/kieudung12/HRI_k68e-re/tree/assignments_4), đặt cạnh B5 rồi build theo mục 3. B5 sử dụng world `lec4_small_room` của workspace đó.

## 2. Cấu trúc thư mục

```text
~/HRI/
├── lec4/                              # Clone riêng từ branch assignments_4
│   ├── lab_env.bash
│   ├── setup_runtime.sh
│   └── src/lec4_robot_lab/
└── b5/                                # Clone từ branch assignments_5
    ├── README.md
    ├── LICENSE
    ├── b5_env.bash                   # Nạp runtime lec4 và overlay B5
    └── src/b5_tb4_lab/
        ├── package.xml
        ├── setup.py
        ├── setup.cfg
        ├── resource/b5_tb4_lab
        ├── launch/
        │   ├── sim.launch.py
        │   └── navigation.launch.py
        ├── maps/
        │   ├── map.yaml
        │   └── map.pgm
        ├── config/goals.yaml
        ├── worlds/chair_target.sdf
        └── b5_tb4_lab/
            ├── __init__.py
            └── autonomous_yolo.py
```

Các thư mục `build/`, `install/`, `log/`, cache Python và trọng số YOLO `*.pt` được loại khỏi Git. Trọng số sẽ được Ultralytics tải khi chạy lần đầu nếu chưa có trên máy.

## 3. Cài đặt và chuẩn bị môi trường

### 3.1. Yêu cầu hệ thống

- Ubuntu 22.04 LTS, ROS 2 Humble và Python 3.10.
- TurtleBot 4 Simulation, Gazebo Fortress, Nav2 và RViz2.
- Phiên desktop có GUI để mở Gazebo, RViz2 và cửa sổ OpenCV.
- Kết nối Internet cho bước cài dependency, chuẩn bị runtime TF2 và tải model YOLO lần đầu.

Clone hai branch thành hai workspace cạnh nhau trên máy mới:

```bash
mkdir -p ~/HRI
git clone --single-branch --branch assignments_4 https://github.com/kieudung12/HRI_k68e-re.git ~/HRI/lec4
git clone --single-branch --branch assignments_5 https://github.com/kieudung12/HRI_k68e-re.git ~/HRI/b5
```

Nếu đã có thư mục `lec4` hoặc `b5`, dùng workspace sẵn có thay vì clone đè lên thư mục đó. `lec4` cần có `lab_env.bash`, `setup_runtime.sh` và `src/lec4_robot_lab/`. Các file runtime được đối chiếu trong lần rà soát này tương ứng với commit `997f251` của branch `assignments_4`.

Nếu dùng đường dẫn khác `~/HRI`, thay đường dẫn trong các lệnh bên dưới nhưng vẫn giữ `lec4` và `b5` cạnh nhau để `../lec4` còn đúng.

### 3.2. Cài đặt các gói phụ thuộc

Thực hiện sau khi đã cài ROS 2 Humble và môi trường mô phỏng TurtleBot 4:

```bash
sudo apt update
sudo apt install -y \
  git build-essential cmake \
  python3-pip python3-colcon-common-extensions python3-rosdep \
  ros-humble-turtlebot4-navigation \
  ros-humble-nav2-simple-commander \
  ros-humble-cv-bridge \
  ros-humble-ros-gz-sim \
  python3-yaml python3-opencv
```

Cài các phiên bản thư viện Python đã dùng trong môi trường bài thực hành:

```bash
python3 -m pip install --user \
  'numpy==1.26.4' \
  'opencv-python==4.10.0.84' \
  'ultralytics==8.4.178'
```

`cv_bridge` cài từ apt trong môi trường ROS Humble này được build với NumPy 1.x. Ghim NumPy 1.26.4 tránh lỗi ABI `_ARRAY_API not found` và crash khi chuyển đổi ảnh. OpenCV Python cũng được ghim để tránh dependency tự nâng NumPy lên 2.x.

### 3.3. Thiết lập môi trường và build package

Build dependency `lec4` trước, sau đó build B5. Trên máy chưa khởi tạo `rosdep`, chạy một lần:

```bash
sudo rosdep init
```

Cài dependency của `lec4` và chuẩn bị runtime:

```bash
rosdep update
cd ~/HRI/lec4
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
bash setup_runtime.sh
source ./lab_env.bash
colcon build --packages-select lec4_robot_lab --symlink-install
source install/setup.bash
ros2 pkg prefix lec4_robot_lab
```

`setup_runtime.sh` build thư viện TF2 ROS riêng trong `.runtime/` theo cấu hình của bài `lec4`; không ghi đè thư viện ROS hệ thống. Lần chạy đầu cần tải source và biên dịch thư viện này.

Build B5:

```bash
cd ~/HRI/b5
source ../lec4/lab_env.bash
colcon build --packages-select b5_tb4_lab --symlink-install
source ./b5_env.bash
ros2 pkg prefix b5_tb4_lab
ros2 pkg executables b5_tb4_lab
```

Lệnh cuối phải có executable `b5_tb4_lab autonomous_yolo`. Trong **mỗi terminal mới** dùng cho B5, chạy `cd ~/HRI/b5` và `source ./b5_env.bash`. Script nạp ROS/domain/Gazebo runtime của `lec4` rồi overlay B5.

## 4. Hướng dẫn chạy

Mở ba terminal theo thứ tự dưới đây. Chỉ chạy một simulator và một stack localization/Nav2 cho mỗi phiên. Dừng các launch cũ trước khi khởi động lại để tránh TF và `/clock` của nhiều phiên chồng nhau.

### 4.1. Khởi chạy Gazebo

**Terminal 1:**

```bash
cd ~/HRI/b5
source ./b5_env.bash
ros2 launch b5_tb4_lab sim.launch.py model:=lite gui:=true rviz:=false
```

Robot xuất hiện trong world `lec4_small_room`. B5 xóa landmark hộp phía đông nam rồi thêm ghế SDF sau khoảng 13 giây kể từ khi launch; chờ log tạo `chair_target` thành công trước khi chạy demo. Vì hình học ghế khác landmark trong map đã lưu, scan quanh vật thể này có thể khác cục bộ so với map.

Kiểm tra publisher cảm biến từ một terminal đã source B5:

```bash
ros2 topic info /scan
ros2 topic info /oakd/rgb/preview/image_raw
```

### 4.2. Nạp bản đồ và khởi chạy AMCL/Nav2

**Terminal 2:**

```bash
cd ~/HRI/b5
source ./b5_env.bash
ros2 launch b5_tb4_lab navigation.launch.py
```

Launch nạp cặp map trong `src/b5_tb4_lab/maps/`, khởi chạy AMCL và mở RViz2 bằng cấu hình `lec4_robot_lab`. Giữ `map.yaml` và `map.pgm` cùng thư mục vì YAML tham chiếu ảnh bằng đường dẫn tương đối.

Nav2 chỉ được khởi chạy sau khi localization nhận Initial Pose và TF `map → odom` sẵn sàng. Thực hiện mục 4.3 để tiếp tục.

### 4.3. Đặt Initial Pose trên RViz2

1. Đảm bảo **Fixed Frame** là `map` và bản đồ đang hiển thị.
2. Chọn **2D Pose Estimate**, đặt tâm và hướng robot khớp với vị trí thực tế trong Gazebo. Ở phiên mô phỏng mới, robot spawn gần `(0, 0)`, hướng `+X` (yaw `0`).
3. Chờ scan LiDAR trùng với tường trên bản đồ, kiểm tra trạng thái localization và navigation active trong panel **Navigation 2**.

Cấu hình RViz của `lec4` gửi pose vào `/initialpose_rviz`; node relay điều chỉnh timestamp rồi chuyển tới `/initialpose` cho AMCL. Nếu vừa khởi động lại Gazebo, đặt pose theo vị trí spawn của phiên mới.

### 4.4. Chạy node điều hướng và YOLO

**Terminal 3:**

```bash
cd ~/HRI/b5
source ./b5_env.bash
ros2 run b5_tb4_lab autonomous_yolo --ros-args -p use_sim_time:=true -p image_topic:=/oakd/rgb/preview/image_raw -p display:=true
```

`use_sim_time:=true` giúp các ROS node trong chương trình dùng thời gian `/clock` của Gazebo khi tạo pose. `display:=true` mở cửa sổ desktop **TurtleBot 4 YOLO detections** ở kích thước 960×720; cửa sổ vẫn hiện ảnh camera khi frame không có vật thể được nhận diện. Đây là ảnh preview gốc 320×240 được phóng lên để dễ xem, không làm tăng độ phân giải cảm biến.

Node chờ AMCL/Nav2 sẵn sàng rồi gửi `Goal 1 → Goal 2 → Goal 3` từ `goals.yaml`. Khi đang di chuyển, camera được xử lý song song, kết quả xuất qua cửa sổ OpenCV, topic `/yolo/detections/image` và log terminal. Để xem trên RViz2, thêm display **Image** và chọn topic `/yolo/detections/image`.

Không dùng teleop hoặc công cụ **Nav2 Goal** trên RViz2 trong lúc chương trình chạy. Khi một goal thất bại, node dừng chuỗi; khi đạt hết goal, chương trình kết thúc và cửa sổ camera đóng. `Ctrl+C` dừng chương trình và hủy goal đang thực hiện.

> Nếu thiếu `-p display:=true`, chương trình vẫn xử lý và publish ảnh nhưng không mở cửa sổ camera. Nếu model không tải được, node báo lỗi YOLO và vẫn có thể điều hướng; cần khắc phục lỗi model trước khi quay demo nhận diện.

Các tham số YOLO có thể truyền bằng `--ros-args -p tên:=giá_trị`:

| Tham số | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `image_topic` | `/oakd/rgb/preview/image_raw` | Topic ảnh RGB đầu vào. |
| `annotated_topic` | `/yolo/detections/image` | Topic ảnh đã vẽ kết quả. |
| `model` | `yolov8n.pt` | Tên model hoặc đường dẫn trọng số. |
| `confidence` | `0.20` | Ngưỡng lọc detection tối thiểu. |
| `inference_period` | `0.5` | Khoảng cách tối thiểu giữa hai lần inference theo giây thực; có thể chậm hơn tùy model/CPU. |
| `display` | `false` | Bật/tắt cửa sổ OpenCV. |

Ultralytics tải `yolov8n.pt` nếu file chưa có; lần chạy đầu cần Internet. Để dùng model lớn hơn, dừng node hiện tại rồi chạy:

```bash
ros2 run b5_tb4_lab autonomous_yolo --ros-args -p use_sim_time:=true -p image_topic:=/oakd/rgb/preview/image_raw -p display:=true -p model:=yolov8s.pt -p confidence:=0.20
```

Model lớn hơn có thể cải thiện nhận diện nhưng xử lý chậm hơn trên CPU. `confidence` chỉ lọc detection, không làm tăng score đầu ra. Score còn phụ thuộc góc nhìn và hình dạng vật thể; ghế SDF đơn giản có thể không được phát hiện trong mọi frame.

**Quay video nộp bài:**

1. Mở Gazebo theo mục 4.1, sắp xếp cửa sổ và bắt đầu quay desktop bằng OBS.
2. Thực hiện mục 4.2–4.3 trong khi ghi hình để thấy bản đồ được nạp, thao tác Initial Pose và scan khớp tường.
3. Chạy lệnh ở Terminal 3, đưa cửa sổ camera YOLO vào khung hình cùng RViz2 và terminal có log goal. Ghế nằm gần Goal 3 nên detection có thể rõ nhất tại khu vực đó.
4. Quay đến khi có đủ ba dòng `Goal 1/2/3 reached successfully`, rồi lưu video MP4/MKV. Trước khi quay chính thức, kiểm tra OBS thu được cửa sổ OpenCV.

Khi kết thúc phiên, dừng chương trình điều hướng, sau đó dừng Nav2 ở Terminal 2 rồi Gazebo ở Terminal 1 bằng `Ctrl+C`.

## 5. Cấu hình goal

Node đọc file [`src/b5_tb4_lab/config/goals.yaml`](src/b5_tb4_lab/config/goals.yaml) khi bắt đầu chạy. Các goal hiện tại được kế thừa từ những lần điều hướng thành công trong bài `lec4`:

| Goal | x (m) | y (m) | yaw (rad) |
| --- | ---: | ---: | ---: |
| Goal 1 | -1.00 | 1.10 | 0.29 |
| Goal 2 | 1.01 | 1.07 | 0.28 |
| Goal 3 | 1.02 | -1.07 | -0.34 |

Đây là tọa độ kế thừa, chưa phải bản ghi đo mới bằng Publish Point cho B5. Để khảo sát, dùng **Publish Point** trên RViz2 và đọc:

```bash
ros2 topic echo /clicked_point
```

Publish Point chỉ cung cấp vị trí `(x, y, z)`, không cung cấp yaw. Chọn hướng mong muốn tại goal; yaw tính bằng radian, `0` hướng `+X` và `pi/2` hướng `+Y` trong frame `map`. Pose robot hiện tại xem bằng `ros2 topic echo /amcl_pose`; trường orientation của message là quaternion `(qx, qy, qz, qw)`, cần đổi sang yaw trước khi ghi vào file:

```text
yaw = atan2(2 * (qw*qz + qx*qy), 1 - 2 * (qy*qy + qz*qz))
```

Chọn ít nhất ba điểm trong vùng trống của map, cách vật cản đủ cho robot di chuyển. Cấu trúc mỗi điểm trong YAML:

```yaml
goals:
  - name: Goal 1
    x: -1.00
    y: 1.10
    yaw: 0.29
  # Khai báo tiếp Goal 2, Goal 3; node yêu cầu ít nhất ba điểm.
```

Sau khi sửa file, build lại và source B5 theo mục 3.3 rồi khởi động lại node. Node dùng bản file được cài trong package, không tự đọc lại goal trong khi đang chạy. Nếu đổi map/world, khảo sát lại các điểm; tọa độ của map cũ có thể không còn phù hợp.

## 6. Node, topic và action chính

| Thành phần | Tên | Vai trò |
| --- | --- | --- |
| Executable | `b5_tb4_lab autonomous_yolo` | Điểm vào của chương trình Python, chạy bằng `ros2 run`. |
| Node điều hướng | `/basic_navigator` | Gửi goal bằng Nav2 Simple Commander và theo dõi kết quả. |
| Node nhận diện | `/b5_yolo_camera` | Nhận ảnh, chạy YOLO, vẽ/publish ảnh và log nhãn/confidence. |
| Action Nav2 | `/navigate_to_pose` | Nhận từng pose mục tiêu trong frame `map`. |
| Bản đồ | `/map` | Occupancy grid từ cặp `map.yaml` và `map.pgm`. |
| LiDAR đầu vào | `/scan` | LaserScan từ mô phỏng. |
| LiDAR cho AMCL/Nav2 | `/scan_amcl` | Scan được throttle xuống khoảng 10 Hz; RViz của lab cũng hiển thị topic này. |
| Pose ước lượng | `/amcl_pose` | Vị trí, quaternion và covariance của AMCL trong frame `map`. |
| Initial Pose RViz | `/initialpose_rviz` | Pose khởi tạo gửi từ công cụ 2D Pose Estimate. |
| Initial Pose AMCL | `/initialpose` | Pose sau relay của `lec4`, được AMCL tiếp nhận. |
| Camera RGB | `/oakd/rgb/preview/image_raw` | Topic ảnh đầu vào mặc định. |
| Kết quả YOLO | `/yolo/detections/image` | Ảnh có bounding box, class và confidence. |
| Thời gian mô phỏng | `/clock` | Thời gian Gazebo dùng cho các node bật `use_sim_time`. |
| TF | `map → odom → base_link → laser` | Chuỗi đặt robot và scan vào map; tên frame cảm biến thực tế xem trong header scan. |

Khi các node tương ứng đang chạy, có thể kiểm tra bằng:

```bash
ros2 node list
ros2 action list -t
ros2 topic info /oakd/rgb/preview/image_raw
ros2 topic info /yolo/detections/image
ros2 param get /basic_navigator use_sim_time
```

## 7. Khắc phục sự cố thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `Package 'lec4_robot_lab' not found` | Clone branch `assignments_4` vào `../lec4`, build theo mục 3.3 rồi source `b5_env.bash`. |
| `Package 'b5_tb4_lab' not found` | Trong terminal hiện tại, source `b5_env.bash`; nếu chưa có install, build B5 theo mục 3.3. |
| `../lec4/lab_env.bash: No such file` | Kiểm tra hai workspace nằm cạnh nhau theo mục 2 và đã clone đủ file của `lec4`. |
| `rosdep init` báo đã được khởi tạo | Bỏ qua bước init; tiếp tục `rosdep update`. |
| `_ARRAY_API not found` hoặc crash ở `cv_bridge` | Cài lại các phiên bản NumPy/OpenCV đã ghim ở mục 3.2 rồi khởi động lại node Python. |
| Cửa sổ camera không hiện | Kiểm tra có `-p display:=true`, đang chạy trong desktop GUI và camera có dữ liệu. Có thể dùng RViz Image display trên `/yolo/detections/image`. |
| Camera không có publisher | Kiểm tra Gazebo đang chạy; dùng `ros2 topic list` tìm topic RGB đúng rồi truyền `image_topic`. |
| YOLO báo lỗi tải model | Kiểm tra Internet ở lần chạy đầu hoặc truyền đường dẫn file weights có sẵn bằng tham số `model`. |
| Ảnh có nhưng không có bounding box | Frame hiện tại có thể không có detection vượt ngưỡng; kiểm tra vật thể trong tầm nhìn. Tăng ngưỡng confidence không làm model tự tin hơn. |
| Cửa sổ ảnh đóng sau Goal 3 | Đây là lúc chương trình hoàn thành; ảnh chỉ được xử lý khi node còn chạy. |
| LiDAR lệch tường | Kiểm tra Fixed Frame `map`, Initial Pose, map/world và TF; sai khác cục bộ gần ghế có thể do thay vật thể so với map. |
| Nav2 chưa bắt đầu | Đặt Initial Pose, chờ localization/TF sẵn sàng và các lifecycle node active; kiểm tra không có stack cũ. |

Lệnh chẩn đoán khi scan lệch hoặc localization chưa ổn định:

```bash
ros2 topic echo --once /amcl_pose
ros2 run tf2_ros tf2_echo map base_link
ros2 topic hz /scan_amcl
ros2 topic info /scan_amcl --verbose
```

Các lệnh theo dõi liên tục cần chạy ở terminal riêng và dừng bằng `Ctrl+C`. AMCL trong `lec4` nhận `/scan_amcl`, dùng ngưỡng cập nhật chuyển động 0,25 m hoặc 0,2 rad. Đây là ngưỡng kích hoạt cập nhật, không phải mức sai số localization cho phép. Cần kiểm tra pose, TF/timestamp, đúng map/world và tải xử lý trước khi kết luận nguyên nhân scan lệch hoặc chỉnh tham số.
