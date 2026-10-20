# Process log — Bài thực hành 05 (TurtleBot 4 + Nav2 + YOLO)

Tài liệu này giữ nguyên đề bài và ghi lại tiến trình, quyết định, lỗi cùng tình trạng hoàn thành để làm căn cứ tiếp tục phiên làm việc và soạn báo cáo.

## Đề bài gốc

Sử dụng Ubuntu 22.04, ROS 2 Humble và TurtleBot 4 Simulation đã chuẩn bị ở bài trước. Dùng lại `map.yaml` và `map.pgm` từ tuần trước để chạy Localization (AMCL) trong Gazebo; thiết lập Initial Pose sao cho robot trên RViz2 khớp thực tế và LiDAR trùng tường bản đồ. Khảo sát và ghi ít nhất ba goal `(x, y, yaw)` trong hệ `map`. Viết ROS 2 node tự điều hướng tuần tự qua ít nhất ba goal bằng Nav2 Simple Commander hoặc action `/navigate_to_pose`, không dùng teleop/chuột đặt goal. Đồng thời subscribe ảnh RGB, đổi `sensor_msgs/Image` sang OpenCV qua `cv_bridge`, chạy YOLO, hiển thị hoặc publish ảnh bounding box và in vật thể nhận diện ra terminal.

Dependency tham khảo: `ros-humble-turtlebot4-navigation`, `ros-humble-nav2-simple-commander`, `ros-humble-cv-bridge`, `ultralytics`, `opencv-python`. Python package đã ghim tương thích ROS Humble: `numpy==1.26.4`, `opencv-python==4.10.0.84`.

## Phiên làm việc — 2026-10-16

### Xác nhận phần hiển thị YOLO

- Sau câu hỏi người dùng về output YOLO, đã kiểm tra lại `autonomous_yolo.py`: `result.plot()` vẽ bounding box/nhãn/confidence; node publish ảnh ROS `Image` lên `/yolo/detections/image`; mỗi frame có detection được log ra terminal dưới dạng `class (confidence)`.
- Chạy thực nghiệm gần nhất sau khi sửa NumPy đã ghi `chair (0.37)` và `bench (0.23)` tại Goal 3. Ảnh minh họa `evidence/yolo_chair_detection.jpg` hiển thị bounding box `chair 0.26`.
- Để nhìn trực tiếp trong RViz2, khi node đang chạy, thêm display **Image** rồi đặt topic `/yolo/detections/image`; nếu chưa thêm display thì ảnh vẫn được publish nhưng không tự bật thành cửa sổ RViz.
- Người dùng lưu ý cần quay video demo nộp bài với map/localization RViz, ba goal liên tiếp và cửa sổ camera YOLO cùng lúc. Đã đổi lệnh chạy chính trong README sang `-p display:=true` và thêm checklist quay desktop bằng OBS; bắt đầu ghi hình trước khi chạy node, kết thúc sau Goal 3.
- Người dùng làm rõ muốn chắc chắn camera và detection cùng xuất hiện trên màn hình để OBS quay được. Đã cập nhật cả ví dụ đổi `image_topic` và hướng dẫn video để dùng đồng thời `-p image_topic:=/oakd/rgb/preview/image_raw -p display:=true`; cửa sổ OpenCV hiển thị frame camera đã annotate.
- Người dùng hỏi vì sao score detection chỉ quanh 0.2. Ghi rõ trong README: `confidence=0.20` là ngưỡng nhận detection, không phải score đầu ra; node dùng `yolov8n.pt` trên ghế SDF và camera 320×240 nên hình dạng/góc nhìn ảnh hưởng mạnh. Đã thêm lệnh tùy chọn thử `yolov8s.pt`; chưa thay model mặc định hoặc đo benchmark model lớn hơn.

### Khắc phục lỗi không tìm thấy package khi launch

- Người dùng chạy `ros2 launch b5_tb4_lab navigation.launch.py` trong `~/HRI/b5` nhưng ROS báo `Package 'b5_tb4_lab' not found`; danh sách tìm kiếm chỉ gồm overlay `~/ros2_ws` và `/opt/ros/humble`.
- Đã kiểm tra `b5/install/b5_tb4_lab` có tồn tại và script `b5_env.bash` sẽ source runtime `lec4`, sau đó source `b5/install/setup.bash`. Nguyên nhân phù hợp với lỗi là terminal chưa source script môi trường B5.
- Hướng khắc phục: `cd ~/HRI/b5 && source ./b5_env.bash`, kiểm tra `ros2 pkg prefix b5_tb4_lab`, rồi chạy launch. Nếu package chưa được cài thì build từ workspace B5 rồi source lại. Đã thêm các lệnh này vào README.
- Đã xác minh trong workspace bằng `source ./b5_env.bash && ros2 pkg prefix b5_tb4_lab`; package được tìm thấy tại `/home/kieu/HRI/b5/install/b5_tb4_lab`. Chưa chạy lại launch trong terminal người dùng; bước đó cần họ chạy sau khi source script ở terminal của mình.

### Khắc phục crash `cv_bridge` do NumPy 2

- Người dùng chạy `autonomous_yolo` thì gặp cảnh báo module nhị phân NumPy 1.x không tương thích NumPy 2.2.6, `cv_bridge` báo `AttributeError: _ARRAY_API not found`, callback ảnh segfault. YOLO vẫn nạp model và node khởi động, nhưng quá trình đổi ROS Image sang OpenCV thất bại.
- Kiểm tra Python user-site: `numpy 2.2.6`, `opencv-python 5.0.0.93`, trong khi `ros-humble-cv-bridge` là bản cài apt. Nguyên nhân: NumPy ABI 2.x không tương thích với extension `cv_bridge` được build với ABI 1.x.
- Đã cài tương thích trong user-site: `numpy==1.26.4` và `opencv-python==4.10.0.84` (tránh OpenCV 5, metadata của nó đòi NumPy >=2). README đã cập nhật lệnh cài đặt có ghim phiên bản và ghi chú không nâng NumPy lên 2.x trong môi trường ROS này.
- Xác minh sau sửa: `cv_bridge`, OpenCV 4.10.0 và Ultralytics 8.4.178 cùng import được; YOLO nạp `yolov8n.pt`; chuyển thử ROS `sensor_msgs/Image` rgb8 sang ảnh OpenCV bgr8 thành công với shape `(4, 6, 3)`.
- ROS CLI ban đầu báo daemon lỗi `!rclpy.ok()`; `ros2 daemon stop` rồi truy vấn lại cho thấy các node mô phỏng/Nav2 vẫn hoạt động. Camera `/oakd/rgb/preview/image_raw` có publisher và `/amcl_pose` có dữ liệu.
- Chạy lại `ros2 run b5_tb4_lab autonomous_yolo` sau sửa: YOLO xử lý stream camera không crash; node gửi tuần tự ba goal và log `Goal 1 reached successfully`, `Goal 2 reached successfully`, `Goal 3 reached successfully`. Gần Goal 3 phát hiện `chair (0.37)` và `bench (0.23)` ở một số frame. Node kết thúc sau khi hoàn thành chuỗi goal.

### Khảo sát ban đầu

- `b5/` mới được tạo và trống.
- `lec4/` chứa world `lec4_small_room`, cặp map `src/lec4_robot_lab/maps/map.yaml` + `map.pgm`, launch sim/localization/Nav2 và cấu hình riêng cho ROS domain 92.
- README `lec4` hướng dẫn khởi động Gazebo trước; sau đó chạy `nav.launch.py nav2:=true rviz:=true map:=...`; trong RViz đặt **2D Pose Estimate** rồi chờ localization ready. Launch cũ cũng cung cấp panel Navigation 2, cấu hình scan AMCL 10 Hz và các watchdog cần cho môi trường hiện tại.
- Không tìm thấy root git ở `/home/kieu/HRI`; `lec4` là git repo lồng bên trong. Không sửa file của `lec4`.
- Có sẵn verification JSON của ba goal Nav2 đã đạt thành công: gần `(-1.00, 1.10)`, `(1.01, 1.07)`, `(1.02, -1.07)` (hệ `map`). Các quaternion đã chuyển thành yaw lần lượt xấp xỉ `0.29`, `0.28`, `-0.34` rad. Đây là điểm mẫu kế thừa từ chạy trước; cần khảo sát lại nếu bản đồ hoặc vị trí spawn thay đổi.

### Chạy thử thực tế và điều chỉnh

- Chạy `sim.launch.py`: Gazebo lên thành công; có `/scan`, `/odom` và `/oakd/rgb/preview/image_raw`. RViz2 cũng lên khi chạy `navigation.launch.py`.
- Map B5 load thành công tại `src/b5_tb4_lab/maps/map.yaml`; Nav2 log map `298 x 276` ô, `0.05 m/cell`. AMCL và Nav2 chuyển active sau khi gửi Initial Pose `(0,0,0)` qua `/initialpose_rviz` và relay của `lec4`.
- Lần chạy node đầu phát hiện thiếu `ultralytics`; đã cài Ultralytics 8.4.178 và PyTorch CPU 2.14.1, tải thành công `yolov8n.pt`. Việc ngắt node để cài dependency phát hiện cleanup gọi shutdown ROS hai lần; đã sửa dùng `SignalHandlerOptions.NO`, cancel goal rồi shutdown có điều kiện.
- Chạy lại `autonomous_yolo`: nhận ảnh camera và inference khoảng 2 Hz; Nav2 lần lượt báo `Goal 1 reached successfully`, `Goal 2 reached successfully`, `Goal 3 reached successfully`. Ở lần thử với mannequin đặt trùng landmark, YOLO nhận được class `traffic light` (confidence 0.41 và 0.69), chưa nhận đúng `person`; ảnh xác nhận landmark khối vẫn nằm dưới mannequin.
- Sau đó đặt mannequin đúng trong tầm camera Goal 3, tách khỏi landmark. YOLO nhìn thấy mannequin nhưng không gán `person`; inference trực tiếp ở confidence 0.05 đoán `stop sign` với confidence 0.15, còn ngưỡng mặc định 0.35 không có detection. Kết luận mannequin hình khối tự dựng chưa phải vật thể phù hợp với COCO.
- Thay mục tiêu kiểm tra bằng ghế SDF có mặt ngồi, tựa lưng và bốn chân (class COCO `chair`), đồng thời launch B5 xóa landmark cũ rồi spawn ghế cùng vùng. Cần chạy một vòng cuối để xác nhận class ghế và đủ ba goal.
- YOLOv8n trên ảnh camera của ghế ở confidence 0.35 chưa phát hiện; inference trực tiếp với ngưỡng 0.01 thấy class `chair` confidence 0.259. Hạ mặc định node xuống 0.20 để nhận ghế; cần xác nhận output tích hợp `chair` trong vòng cuối.
- Vòng cuối dùng Gazebo headless (`gui:=false`) để tránh GUI Gazebo tranh tài nguyên đồ họa với RViz trên máy. B5 xóa `landmark_southeast` thành công, tạo `chair_target` thành công; map load, AMCL/Nav2 active sau Initial Pose `(0,0,0)`.
- Node tích hợp nhận ảnh mặc định `/oakd/rgb/preview/image_raw`, publish annotated image `/yolo/detections/image` (publisher đã thấy trong ROS graph), và in class `chair` với confidence `0.21`, `0.27`, `0.32`, `0.49` ở các frame tại gần Goal 3; một frame khác có thêm `bench (0.25)`. Kết quả phụ thuộc góc camera và confidence; một số frame không detect.
- Trong cùng lượt cuối, Nav2 báo cả ba `Goal 1`, `Goal 2`, `Goal 3 reached successfully`. Vì vậy đã chạy thực nghiệm end-to-end đủ ba goal và nhận dạng được ghế.
- Đã lưu ảnh minh họa bounding box `chair 0.26` tại `evidence/yolo_chair_detection.jpg` để dùng làm minh chứng báo cáo.
- Có lần build thất bại sau khi đổi file SDF do artifact build cũ còn tham chiếu `person_mannequin.sdf`; xóa riêng artifact package build/install rồi build lại đã thành công. Cài PyTorch CPU đã nâng setuptools; đồng bộ `packaging` lên 26.3 khắc phục lỗi build `canonicalize_version`.

### Kết luận kiểm thử

- Đạt: B5 build được; map B5 nạp đúng; camera RGB hoạt động; AMCL/Nav2 active sau initial pose; node điều hướng đạt 3/3 goal; YOLO nhận class `chair`, log confidence và tạo annotated image topic.
- Điều kiện thử cuối: `sim.launch.py gui:=false`, `navigation.launch.py` với RViz2 bật, initial pose tại spawn `(0,0,0)`. Dùng Gazebo headless để tránh GPU GUI nặng trên phiên này; các luồng ROS, camera, RViz và Nav2 vẫn chạy.
- Ghi chú báo cáo: các goal là tọa độ đã dùng thành công trong bài lec4; vật thể ghế là SDF spawn bổ sung ở gần landmark đông nam. YOLO không phát hiện trong mọi frame; frame nhìn rõ ghế mới có detection `chair` khoảng 0.21–0.49.

### Đã tạo

- Tạo ROS 2 package Python `b5_tb4_lab`, cặp bản đồ riêng trong package và `b5_env.bash` overlay lên runtime của `lec4`.
- Tạo `sim.launch.py` và `navigation.launch.py` làm wrapper cho launch đã có của `lec4`; localization dùng map được cài trong B5.
- Tạo `config/goals.yaml` với ba goal nêu trên.
- Tạo node `autonomous_yolo`: chờ Nav2 active/AMCL initial pose; gửi từng goal qua `BasicNavigator`; dừng chuỗi nếu goal thất bại; trong executor song song subscribe ảnh, convert bằng `CvBridge`, inference YOLO, log nhãn/confidence và publish ảnh annotated lên `/yolo/detections/image`.
- Tạo README hướng dẫn cài dependency, build và chạy ba terminal.

### Lỗi / giới hạn hiện tại

- Lần `cp` map đầu tiên thất bại do thư mục `maps/` trong package mới chưa tồn tại. Đã tạo thư mục rồi chép lại thành công.
- `colcon build --symlink-install` trong workspace B5 hoàn tất: `1 package finished`.
- `python3 -m py_compile` cho node Python và hai launch file không báo lỗi; `ros2 pkg executables b5_tb4_lab` nhận diện entry point `autonomous_yolo`.
- Đã so sánh `map.yaml` và `map.pgm` trong B5 với nguồn `lec4` bằng `cmp`; cả hai trùng khớp. Kích thước `map.pgm` là 84 KiB.
- Topic camera đã được xác nhận trong vòng chạy cuối là `/oakd/rgb/preview/image_raw`; node cũng hỗ trợ đổi bằng ROS parameter.
- Đã chạy mô phỏng end-to-end trong vòng kiểm thử cuối: AMCL/Nav2 active, camera và YOLO hoạt động, cả ba goal đều reached. Lỗi `Package ... not found` trong phiên hiện tại chưa được xác minh lại sau khi người dùng source `b5_env.bash`.
- Lần chạy đầu có thể cần tải trọng số `yolov8n.pt` qua Internet. Nếu thiếu `ultralytics`/weights, node log lỗi nhận diện nhưng vẫn tiếp tục điều hướng.

### Tiếp tục từ đây

1. Môi trường B5 đã build và được chạy end-to-end trước đây: localization/Nav2 active, camera/YOLO xử lý ảnh, ba goal đạt và có detection ghế. Nếu đổi máy hoặc source, cài workspace `lec4` trước theo README mới.
2. Trước video nộp bài, mở ba terminal, source `b5_env.bash` ở mỗi terminal; chạy Gazebo, localization/Nav2, đặt Initial Pose và đợi scan khớp map.
3. Bắt đầu quay màn hình rồi chạy `autonomous_yolo` với `-p display:=true`; lưu video sau khi Goal 3 hoàn tất.
4. Nếu thay map hoặc tọa độ goal, cập nhật `goals.yaml` và nhật ký/report; kiểm tra lại an toàn đường đi trước khi quay.

### Rà soát và viết lại README chuyên nghiệp

- Người dùng yêu cầu rà kỹ workspace và viết lại README, tham khảo `lec4/README.md`, đồng thời làm rõ B5 phụ thuộc vào workspace bài trước và không độc lập nếu ZIP thiếu `lec4`.
- Đã đối chiếu cấu trúc B5, package metadata, hai launch wrapper và `b5_env.bash` với README của workspace/package lec4. Xác nhận B5 launch tra cứu `lec4_robot_lab`; môi trường source `../lec4/lab_env.bash`; lec4 còn có `setup_runtime.sh` và các bước rosdep/build riêng.
- Viết lại README theo cấu trúc hướng dẫn: cảnh báo phụ thuộc lec4, cấu trúc workspace, yêu cầu/cài build lec4 trước B5, chạy simulation-localization-Nav2-YOLO, goal mẫu, quay video demo và bảng troubleshooting. Nêu rõ goal là dữ liệu kế thừa từ lec4, khác biệt giữa ngưỡng confidence và score YOLO, hiển thị desktop cần `display:=true`, cùng giới hạn khi thiếu workspace lec4.
- Chưa thực hiện build/chạy thử; đây là cập nhật tài liệu dựa trên việc rà soát source và hướng dẫn hiện có.

## Phiên làm việc — 2026-10-20

### Điều tra hiện tượng scan LiDAR lệch bản đồ khi robot di chuyển

- Người dùng báo đôi lúc dữ liệu LiDAR `/scan` không trùng tường map khi robot đang di chuyển.
- Đối chiếu cấu hình lec4 mà B5 gọi lại: AMCL dùng `/scan_amcl`; `scan_throttle.py` chuyển `/scan` thành `/scan_amcl` ở 10 Hz với QoS queue độ sâu 1 để ưu tiên scan mới; các ngưỡng cập nhật AMCL là `update_min_d: 0.25 m`, `update_min_a: 0.2 rad`; frames là `map`, `odom`, `base_link`. AMCL chờ người dùng đặt initial pose trong RViz.
- Map B5 có resolution 0.05 m/cell, origin `[-7.1, -6.55, 0]`. Launch B5 dùng world `lec4_small_room`; thay landmark hộp phía đông nam bằng ghế SDF nên có thể khác cục bộ so với occupancy grid đã lưu.
- Đã thêm mục chẩn đoán vào README: Fixed Frame `map`, đặt lại Initial Pose khi robot đứng, xem `/amcl_pose`, `tf2_echo map base_link`, tần số và publisher/subscriber `/scan_amcl`, dừng stack trùng và xác nhận map/world đúng.
- Chưa kiểm tra ROS graph/runtime tại thời điểm người dùng gặp lệch và chưa thay tham số AMCL; cần log/quan sát để phân biệt initial pose, TF/odometry, scan bị trễ, stack trùng hay vật cản thay đổi.

## Phiên làm việc — 2026-10-20 (tái cấu trúc README theo phần bài tập)

- Người dùng muốn README chuyên nghiệp để đưa lên GitHub và chia nội dung thành Phần 1, 2, 3, ... theo đề bài.
- Tái cấu trúc `README.md` thành phần chuẩn bị/cài đặt, Phần 1 localization, Phần 2 khảo sát goal, Phần 3 điều hướng Nav2 bằng node, Phần 4 YOLO camera, nội dung video cần nộp và troubleshooting.
- Giữ cảnh báo phụ thuộc `lec4` ở đầu trang; làm rõ package/runtime không có trong B5 và người đọc GitHub phải lấy workspace tuần trước riêng rồi cài/build trước.
- Bổ sung mục lục, mô tả output của node (cửa sổ OpenCV, image topic, terminal), ghi rõ tọa độ goal hiện tại chỉ là tọa độ kế thừa chứ không phải số đo mới, và giữ các ghi chú về NumPy/scan/AMCL.
- Chỉ chỉnh tài liệu; không build hoặc chạy mô phỏng trong phiên này.

## Phiên làm việc — 2026-10-20 (áp dụng khung README người dùng cung cấp)

- Người dùng cung cấp cấu trúc mục lục mong muốn cho README: Giới thiệu; Cấu trúc thư mục; Cài đặt và chuẩn bị môi trường với ba tiểu mục; Hướng dẫn chạy với bốn tiểu mục; Cấu hình goal; Node/topic/action; Khắc phục sự cố.
- Viết lại README B5 theo đúng cấu trúc và tiêu đề đã yêu cầu. Bổ sung bảng node/topic/action, tách hướng dẫn chạy thành Gazebo, AMCL/Nav2, Initial Pose và node điều hướng + YOLO; giữ rõ dependency lec4 bắt buộc, các goal chỉ là tọa độ mẫu kế thừa và phần quay video nộp bài.
- Chỉ chỉnh tài liệu; chưa build hoặc chạy mô phỏng trong phiên này.

## Phiên làm việc — 2026-10-20 (chuẩn bị publish branch assignments_5)

- Người dùng yêu cầu commit/push B5 lên `kieudung12/HRI_k68e-re`, branch `assignments_5`, theo yêu cầu repository Public chứa source, launch, map, config và README.
- Xác nhận repository đang Public qua GitHub CLI. Remote branch `assignments_5` tồn tại nhưng hiện đang chứa package UR3 của bài khác; chuẩn bị thay nội dung root bằng B5 để branch và trang repository khớp đúng bài nộp. Lịch sử commit trước vẫn được giữ.
- Dùng clone tạm độc lập vì `/home/kieu/HRI` không phải git repo, B5 nằm ngoài git repo lec4, còn `lec4` đang có nhiều thay đổi staged không liên quan. Không đưa thay đổi lec4 vào commit.
- Tôn trọng `.gitignore` của B5 (`*.pt`): README được sửa để nói Ultralytics tải `yolov8n.pt`/`yolov8s.pt` tự động khi cần; không commit model weights nhị phân. Cặp map, source package, launch, config, README, process log và ảnh evidence được giữ trong payload B5.
- Đã commit và push B5 lên `origin/assignments_5`; bản đầu là `37199f5`, sau khi bổ sung log đã amend và push thành `79d5536`. Repository được xác nhận Public. Không chạy build/test trong phiên publish này.

## Phiên làm việc — 2026-10-20 (làm rõ cửa sổ camera ở terminal 3)

- Người dùng nhắc terminal 3 cần làm hiện ảnh camera nhìn rõ.
- Node vốn đã có `display:=true` để mở OpenCV, nhưng ảnh input preview 320×240 khiến cửa sổ gốc nhỏ. Đã đổi sang `cv2.WINDOW_NORMAL` và resize cửa sổ lên 960×720 để dễ xem/ghi OBS; ảnh vẫn được annotate và publish như trước.
- README làm rõ đây là cửa sổ desktop riêng khởi chạy từ terminal 3 (không phải ảnh inline trong terminal) và yêu cầu phiên GUI.
- Chưa chạy kiểm thử GUI trong phiên này.

### Khắc phục lệnh Terminal 3 không mở cửa sổ camera

- Người dùng gửi ảnh desktop: terminal có log `b5_yolo_camera` nhưng không thấy cửa sổ preview. Lệnh đang chọn trong IDE chỉ truyền `image_topic`; trong code `display` mặc định là `false`, nên YOLO vẫn subscribe/inference/log nhưng không gọi `imshow`.
- README hiện tại đã có `display:=true`, nhưng để tránh sao chép nhầm lệnh cũ, đổi lệnh chính thành một dòng và thêm cảnh báo rõ rằng thiếu `display:=true` sẽ không mở cửa sổ.
- Cách chạy đúng: `ros2 run b5_tb4_lab autonomous_yolo --ros-args -p image_topic:=/oakd/rgb/preview/image_raw -p display:=true` trong terminal desktop đã source `b5_env.bash`.

## Phiên làm việc — 2026-10-20 (rà soát trước lần push tiếp theo)

- Người dùng yêu cầu kiểm tra kỹ lại source và README rồi push cập nhật lên GitHub.
- Đã đối chiếu README với node, hai launch, setup/package metadata, cấu hình goals, map và runtime lec4. Branch remote `assignments_4` có đầy đủ runtime; các file environment, setup_runtime, AMCL/Nav2, RViz và launch được đối chiếu byte với local và đều trùng khớp (commit lec4 được kiểm tra: `997f251`).
- Các điểm cần bổ sung/sửa: lệnh clone dependency lec4; ROS simulation time trong lệnh node; phân biệt executable với node `basic_navigator` và `b5_yolo_camera`; đường relay `/initialpose_rviz → /initialpose`; Publish Point không cung cấp yaw; cửa sổ camera kết thúc cùng chương trình; quy trình quay video bắt đầu trước nạp map/Initial Pose.
- Build `colcon build --packages-select b5_tb4_lab --symlink-install` thành công (1 package). Đã kiểm tra cú pháp 14 khối lệnh Bash trong README, Python/XML, link file nội bộ, launch argument generation và các map/goal/world/launch assets được cài; đều đạt.
- Phát hiện lỗi thực khi smoke GUI cũ: node có tạo cửa sổ và publish ảnh nhưng tiến trình không thoát, bị timeout sau 35 giây. Đã chuyển toàn bộ OpenCV HighGUI sang luồng chính, giữ inference và các lệnh Nav2 blocking trên các luồng riêng; dùng event để dừng/hủy goal trước cleanup. Bổ sung dependency trực tiếp `ros_gz_sim` trong package metadata.
- Kiểm thử console entrypoint thực với YOLOv8n, ảnh RGB tổng hợp 320x240, cửa sổ desktop thật và ROS domain riêng 192 (không gửi lệnh cho robot mô phỏng đang mở): (1) ảnh được đổi bgr8/publish, giữ header và hiện cửa sổ trong lúc chưa có Nav2; Ctrl+C thoát sạch; (2) lifecycle/action Nav2 giả lập nhận đúng ba goal theo thứ tự, frame map và timestamp simulation 42 s, có đủ ba log reached và đóng cửa sổ/thoát mã 0; (3) Ctrl+C khi goal đang chạy gửi cancel, không gửi goal tiếp và thoát mã 0. Cả ba trường hợp đều đạt sau sửa, không có traceback.
- Hai map B5 được so sánh byte với branch Public `assignments_4` và trùng khớp. Ba goal nằm trong ô free; khoảng cách 2D xấp xỉ tới ô không free gần nhất lần lượt 0.77/0.69/0.68 m. Đây chỉ là kiểm tra vị trí goal, không xác nhận lại đường đi không va chạm trong Gazebo.
- README giữ đúng bảy mục người dùng yêu cầu; thêm clone lec4/B5, lệnh simulation time, giải thích quaternion/yaw, node/topic/relay thực tế, cách quay đủ bước nạp map/localization và vòng đời cửa sổ camera. Dùng các phiên bản NumPy/OpenCV/Ultralytics đang cài để hạn chế khác biệt dependency.
- GitHub được xác nhận vẫn Public. Chuẩn bị commit cập nhật README/source/metadata/process vào branch `assignments_5` bằng checkout riêng, giữ nguyên working tree lec4. Không chạy lại toàn bộ mô phỏng Gazebo trong lần rà này; ba goal ở kiểm thử mới là action giả lập.
