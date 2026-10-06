# Bài thực hành 03 – LLM Skill Planning với Camera và Gripper

Project ROS 2 mô phỏng UR3e thực hiện nhiệm vụ phân loại các block màu trên bàn. Hệ thống sử dụng camera để nhận biết vị trí block và trạng thái zone, LLM để sinh kế hoạch ở mức skill, MoveIt 2 để lập quỹ đạo cho tay máy và Robotiq 2F-85 để gắp vật.

## 1. Nhiệm vụ

Mô hình gồm:

- UR3e trong Gazebo Fortress / Gazebo Sim.
- Gripper Robotiq 2F-85.
- Một camera RGB cố định nhìn xuống bàn.
- Năm block màu: `red_cube`, `yellow_cube`, `blue_cube`, `green_cube`, `purple_cube`.
- Ba zone được đánh dấu trực quan là **A**, **B**, **C**, tương ứng với `zone_a`, `zone_b`, `zone_c`.
- LLM lập kế hoạch từ câu lệnh tự nhiên như `Put the red cube in Zone B.`.
- Camera cung cấp trạng thái môi trường cho planner và bộ thực thi.

Khi zone đích đang có block, hệ thống phải dọn zone trước rồi mới thực hiện `pick` và `place` cho block được yêu cầu.

## 2. Kiến trúc hệ thống

```text
Natural Language Command
          |
          v
     LLM Planner
          |
          v
    Structured JSON Plan
          |
          v
      Plan Validator
          |
          v
     Robot Skills
       /       \
      v         v
  MoveIt 2   Gripper Controller
       \       /
        v     v
          Gazebo

Camera RGB
    |
    v
  Perception (OpenCV HSV)
    |
    v
/environment_state
    |
    +--> Plan Validator / Robot Skills
    +--> /perception/debug_image
```

LLM chỉ sinh các skill được phép. Validator kiểm tra cấu trúc kế hoạch, object, zone, thứ tự thao tác và trạng thái camera trước khi robot di chuyển.

## 3. Chức năng chính

- Nhận ảnh từ camera RGB qua `/camera`.
- Phân đoạn năm block theo màu bằng HSV, morphology và contour.
- Tính vị trí block trên mặt bàn từ ảnh camera và mô hình chiếu cố định.
- Xác định zone nào đang trống hoặc đang có block.
- Xuất trạng thái môi trường dưới dạng JSON qua `/environment_state`.
- Xuất ảnh debug có contour, centroid, tên block, zone và trạng thái xử lý.
- Lập kế hoạch chuyển động bằng MoveIt 2.
- Điều khiển gripper Robotiq qua `ros2_control`.
- Xử lý zone bị chiếm bằng các vị trí tạm trên bàn.
- Kiểm tra kế hoạch LLM trước khi thực thi.

## 4. Cấu trúc thư mục

```text
ur3_b3/
├── README.md
└── src/ur3_b3/
    ├── package.xml                  # Metadata và dependency của package
    ├── setup.py                      # Cài package và console scripts
    ├── setup.cfg
    ├── resource/ur3_b3
    ├── launch/
    │   ├── sim.launch.py             # Gazebo, controller, bridge và perception
    │   └── moveit.launch.py          # MoveIt 2 cho UR3e + Robotiq
    ├── config/
    │   ├── controllers.yaml          # ros2_control và tham số chuyển động
    │   └── ur3e_robotiq.srdf.xacro   # Nhóm MoveIt và collision rules
    ├── urdf/
    │   └── ur3e_robotiq.urdf.xacro   # UR3e, adapter và gripper Robotiq
    ├── worlds/
    │   └── table.sdf                 # Bàn, zone, block và camera
    └── ur3_b3/
        ├── perception.py             # Nhận dạng block từ ảnh camera
        ├── planner.py                # Gọi LLM và validate plan
        ├── skills.py                 # IK, MoveIt, gripper và staging
        └── task.py                   # CLI entry point
```

Các thư mục sinh tự động như `build/`, `install/` và `log/` không thuộc mã nguồn cần theo dõi trên Git.

## 5. Yêu cầu môi trường

- Ubuntu 22.04.
- ROS 2 Humble.
- Gazebo Fortress / Gazebo Sim 6.
- MoveIt 2.
- `ur_description` và `ur_simulation_gz`.
- `robotiq_description`.
- `ros_gz_sim` và `ros_gz_bridge`.
- `controller_manager` và `gripper_controllers`.
- OpenCV, `cv_bridge`, NumPy, PyYAML và Python `requests`.
- Một endpoint LLM tương thích OpenAI Chat Completions nếu chạy chế độ LLM.

Các package UR, Robotiq và `ros_gz` cần được build trong một workspace dependency, sau đó source workspace đó trước khi build project này. Trong các lệnh dưới đây workspace dependency được minh họa là `~/ros2_ws`.

## 6. Build

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

cd ~/HRI/ur3_b3
colcon build --symlink-install
source install/setup.bash
```

Nếu thay đổi `config/controllers.yaml`, hãy build lại và source `install/setup.bash` trước khi chạy task.

## 7. Chạy mô phỏng

Nên dùng hai terminal và chỉ chạy một instance MoveIt 2.

### Terminal 1: Gazebo, controller, camera bridge và perception

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
source ~/HRI/ur3_b3/install/setup.bash

ros2 launch ur3_b3 sim.launch.py gui:=true
```

Đặt `gui:=false` nếu chỉ cần chạy mô phỏng không mở giao diện Gazebo.

### Terminal 2: MoveIt 2

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
source ~/HRI/ur3_b3/install/setup.bash

ros2 launch ur3_b3 moveit.launch.py
```

Sau khi khởi động, mô phỏng có UR3e, Robotiq 2F-85, bàn, năm block, ba zone và camera overhead. Không chạy đồng thời nhiều `moveit.launch.py` vì sẽ tạo nhiều action server `/execute_trajectory`.

## 8. Kiểm tra camera và perception

Camera được bridge vào các topic:

```bash
ros2 topic list -t | grep camera
ros2 topic hz /camera
ros2 topic hz /camera_info
ros2 topic echo --once /camera --field width
```

Mở ảnh debug:

```bash
ros2 run rqt_image_view rqt_image_view /perception/debug_image
```

Theo dõi trạng thái môi trường:

```bash
ros2 topic echo /environment_state
```

`/perception/debug_image` hiển thị ảnh camera, contour, bounding box, centroid, tên block, đường viền zone và trạng thái `COMPLETE` hoặc `INCOMPLETE`.

`/environment_state` chứa vị trí nhìn thấy của từng block, trạng thái các zone, danh sách block chưa nhìn thấy và nguồn dữ liệu `camera_rgb_hsv`. Planner chỉ chấp nhận state hoàn chỉnh; vị trí block không được lấy trực tiếp từ entity pose của Gazebo.

## 9. Chạy nhiệm vụ bằng LLM

Đặt endpoint và model LLM. Ví dụ với dịch vụ 9Router chạy local:

```bash
export NINEROUTER_BASE_URL='http://localhost:20128/v1'
export NINEROUTER_MODEL='ag/gemini-3.8-flash-medium'

ros2 run ur3_b3 task \
  --command 'Put the red cube in Zone B.'
```

Luồng xử lý:

1. Đọc state mới nhất từ camera.
2. Gửi câu lệnh và state cho LLM.
3. Nhận JSON gồm các skill `clear_zone`, `pick`, `place`, `home`.
4. Validate toàn bộ plan.
5. Thực thi plan bằng MoveIt 2 và gripper.

Có thể xem plan mà không thực thi bằng `--dry-run`:

```bash
ros2 run ur3_b3 task \
  --command 'Put the red cube in Zone B.' \
  --dry-run
```

### API key

Nếu chưa có `NINEROUTER_API_KEY`, node sẽ hỏi key trong terminal. Sau request thành công, key được lưu tại:

```text
~/.config/ur3_b3/9router_api_key
```

File được tạo với quyền `600`. Có thể chỉ định vị trí khác bằng:

```bash
export NINEROUTER_KEY_FILE='/path/to/key'
```

Hoặc đặt key trực tiếp trong phiên làm việc:

```bash
export NINEROUTER_API_KEY='YOUR_KEY'
```

## 10. Robot skills

| Skill | Vai trò |
| --- | --- |
| `home` | Đưa tay máy về tư thế home sau khi hoàn tất thao tác. |
| `pick` | Đọc vị trí block từ camera, mở gripper, tiếp cận, gắp và nâng block. |
| `place` | Di chuyển đến zone hoặc vị trí tạm, mở gripper, nâng tay và xác nhận bằng camera. |
| `clear_zone` | Tìm block đang chiếm zone, chọn vị trí tạm còn trống rồi chuyển block ra ngoài. |
| `find_free_position` | Skill nội bộ chọn staging cell không bị chiếm và có thể tiếp cận bằng MoveIt. |

Các vị trí tạm được kiểm tra theo cả `environment_state` và khả năng lập kế hoạch tới hover pose. Mục tiêu là hỗ trợ nhiều block phải di chuyển trước khi đặt block yêu cầu.

## 11. Topic và interface quan trọng

| Topic / interface | Kiểu | Vai trò |
| --- | --- | --- |
| `/camera` | `sensor_msgs/msg/Image` | Ảnh RGB đầu vào từ camera. |
| `/camera_info` | `sensor_msgs/msg/CameraInfo` | Tham số camera dùng khi quy đổi pixel sang mặt bàn. |
| `/perception/debug_image` | `sensor_msgs/msg/Image` | Ảnh đã vẽ kết quả perception. |
| `/environment_state` | `std_msgs/msg/String` | JSON về block, zone, missing và trạng thái hoàn chỉnh. |
| `/joint_states` | `sensor_msgs/msg/JointState` | Trạng thái joint của arm và gripper. |
| `/gripper_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` | Điều khiển đóng/mở Robotiq. |
| `/compute_ik` | `moveit_msgs/srv/GetPositionIK` | Kiểm tra IK cho pose tiếp cận. |
| `/compute_cartesian_path` | `moveit_msgs/srv/GetCartesianPath` | Tạo đoạn tiếp cận và rút tay theo Cartesian path. |
| `/plan_kinematic_path` | `moveit_msgs/srv/GetMotionPlan` | Lập kế hoạch tới hover pose. |
| `/execute_trajectory` | `moveit_msgs/action/ExecuteTrajectory` | Thực thi quỹ đạo arm qua MoveIt. |

## 12. Tham số chính

Các tham số chạy hiện tại nằm trong [`src/ur3_b3/config/controllers.yaml`](src/ur3_b3/config/controllers.yaml):

```yaml
robot_skills:
  ros__parameters:
    velocity_scaling: 0.2
    acceleration_scaling: 0.1
    gripper_motion_time: 3.0
    gripper_close_position: 0.52
```

- `velocity_scaling`: hệ số tốc độ lập kế hoạch cho arm.
- `acceleration_scaling`: hệ số gia tốc lập kế hoạch cho arm.
- `gripper_motion_time`: thời gian gửi trajectory đóng/mở gripper, tính bằng giây.
- `gripper_close_position`: vị trí đóng knuckle của Robotiq; giá trị hiện tại được cân chỉnh cho block 35 mm.

Giá trị nhỏ hơn của hai hệ số đầu làm chuyển động arm chậm hơn. Sau khi đổi YAML, cần build lại package và source `install/setup.bash`.

## 13. Kịch bản kiểm thử

### 13.1. Camera

- Khởi động mô phỏng và mở `/perception/debug_image`.
- Kiểm tra năm block được nhận dạng theo màu.
- Di chuyển một block vào zone A, B hoặc C trong Gazebo.
- Theo dõi `/environment_state` để kiểm tra `location` của block và occupant của zone thay đổi theo ảnh camera.

### 13.2. Gripper

- Kiểm tra gripper mở trước thao tác `pick`.
- Quan sát hai pad tiếp xúc với hai mặt bên của block.
- Kiểm tra arm nâng block sau khi `close_gripper()` hoàn tất.
- Theo dõi `/joint_states` nếu cần kiểm tra vị trí knuckle.

### 13.3. Zone đích đang bị chiếm

Ví dụ zone B đang có `blue_cube`, người dùng yêu cầu:

```text
Put the red cube in Zone B.
```

Kế hoạch hợp lệ cần có dạng:

```json
{
  "plan": [
    {"skill": "clear_zone", "zone": "zone_b"},
    {"skill": "pick", "object": "red_cube"},
    {"skill": "place", "object": "red_cube", "target": "zone_b"},
    {"skill": "home"}
  ]
}
```

Trong đó `clear_zone` sẽ:

1. Nhận biết occupant của zone B từ camera.
2. Tìm một staging cell còn trống và có thể tiếp cận.
3. Gắp `blue_cube` và đặt ra vị trí tạm.
4. Cho phép plan tiếp tục gắp `red_cube`.
5. Đặt `red_cube` vào zone B và đưa arm về `home`.

## 14. Giới hạn hiện tại

- Perception dựa trên màu HSV và phù hợp với bối cảnh block màu đơn giản.
- Camera có vị trí cố định và phép chiếu mặt bàn được hiệu chỉnh cho world hiện tại.
- Vị trí tạm là các staging cell được khai báo trong `skills.py`, nên vẫn phụ thuộc kích thước bàn và workspace của robot.

