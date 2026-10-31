# Kiểm thử phiên bản B7 độc lập — 30/10/2026

Môi trường: Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, TurtleBot 4 lite; NVIDIA RTX 4060 8 GB. Nguồn ROS chỉ từ `/opt/ros/humble` và B7, không source workspace bài khác. Model Whisper large-v3 chạy CUDA FP16, được lưu trong `b7/models`.

| Câu lệnh | Bản chép Whisper | Tuyến Nav2 | Kết quả |
| --- | --- | --- | --- |
| Đi đến khu vực A. | Đi đến khu vực A. | A | Đạt |
| Di chuyển từ khu vực A đến khu vực B. | Di chuyển từ khu vực A đến khu vực B. | A → B | Đạt |
| Đi đến phòng thí nghiệm. | Đi đến phòng thí nghiệm. | C | Đạt |
| Đi đến khu vực D. | Đi đến khu vực D. | Từ chối, không gửi goal | Đạt |
| Đi từ phòng A qua khu vực C rồi đến phòng B. | Đi từ phòng A qua khu vực C rồi đến phòng B. | A → C → B | Đạt |

Mỗi goal hợp lệ nhận status `4` (SUCCEEDED) từ Nav2. Thời gian đo gồm Gazebo/RViz đang chạy; model nhận mỗi file khoảng 1,1–4,3 giây. Dữ liệu chi tiết: `whisper_results.json` và `nav2_results.json`.

Đã thử riêng luồng Enter → PortAudio/PulseAudio → Whisper → ROS bằng tiếng Việt tổng hợp phát vào microphone ảo. Câu ba điểm được nhận đúng và đọc lại đúng trên `/voice_command_test`. `microphone_pipeline.json` lưu kết quả. Đoạn im lặng không tạo bản chép.

Các file kiểm thử là giọng tổng hợp; C/D được viết cách đọc “xê”/“đê” khi tạo âm thanh để TTS không đọc nhầm thành số La Mã. Kết quả không thay thế kiểm tra giọng người và microphone vật lý của người dùng. Model mới và chế độ ghi bằng Enter chưa được xác nhận với giọng thật của người dùng trong lần này.

Gazebo GUI mới được mở sau khi có odometry/scan; scan vẫn cập nhật sau khi mở giao diện. AMCL và các node Nav2 đều active. Các kiểm thử parser, vùng không tồn tại và đổi tọa độ đều đạt.

Đã giải nén bản nguồn sang `/tmp/b7_portable_check/b7`, build và chạy kiểm thử parser thành công, đọc được launch arguments của cả mô phỏng lẫn Nav2. Prefix khi thử bản di chuyển chỉ gồm bản build tại `/tmp` và `/opt/ros/humble`. Chạy lại `bash setup.sh` trên B7 cũng hoàn thành: cài dependency, build, kiểm tra model local và sinh ảnh phân vùng.

Cập nhật parser theo câu người dùng: hỗ trợ “đi đến khu A”, “đi khu A rồi sang khu B rồi sang khu C”, “sau đó sang”. Đã chạy 6 nhóm kiểm thử đơn vị, gồm giữ đủ điểm đầu của câu ngắn và từ chối toàn bộ tuyến nếu có vùng không tồn tại hoặc thiếu đích. Package build thành công.

Đối chiếu lại yêu cầu phân vùng: thay khoảng cách thẳng bằng BFS đa nguồn qua các ô trống, tường ngăn lan nhãn. 3 vùng A/B/C đều liên thông, không tô ô vật cản/chưa biết; khoảng cách goal đến ô không trống lần lượt 0,92 / 0,88 / 1,50 m, vượt ngưỡng 0,22 m. `segmentation_results.json` lưu dữ liệu. Tổng cộng 9 nhóm kiểm thử đạt sau thay đổi; build và sinh lại `regions.png` thành công.

Ngày 31/10/2026: tái hiện lỗi từ ảnh người dùng, bản chép “Di chuyển đến khu vực A cho tôi.” bị báo “Thiếu tên khu vực” vì cả “tôi” và “tới” đều được bỏ dấu thành `toi`. Parser nay bỏ đuôi lịch sự trước khi tách tuyến, hỗ trợ “cho tôi”, “giúp tôi với” và các biến thể mình/em. Kiểm thử cả câu gốc, tuyến nhiều điểm có đuôi lịch sự và vùng D vẫn bị từ chối; tổng cộng 11 nhóm kiểm thử đạt. Kiểm tra phiên đang chạy: action `NavigateToPose` sẵn sàng, controller_server và bt_navigator đều active. Đây là xác nhận parser và trạng thái Nav2, chưa phải một lượt robot di chuyển mới; cần khởi động lại voice_navigator đang chạy để nạp sửa đổi.

Cùng ngày, bản giao diện đầu tiên: chỉnh RViz sang góc nhìn 2D không xoay, nền sáng, ba vùng màu nhẹ, nhãn phòng/đích và biểu tượng robot có hướng. Costmap/laser/footprint được gom vào nhóm Diagnostics và tắt hiển thị mặc định; dữ liệu điều hướng vẫn giữ nguyên. Node map_markers phát 17 marker với QoS transient-local; subscriber vào sau nhận được đủ dữ liệu. Lớp tô dùng các hình chữ nhật ghép từ từng hàng ô trống thành 642 tam giác; diện tích A/B/C khớp phân vùng lần lượt 20,09 / 19,905 / 33,90 m², không tô xuyên tường. Đã kiểm tra trực tiếp RViz: Global Status và marker Status đều OK, Navigation/Localization active. Package build thành công, 11 nhóm kiểm thử hiện có vẫn đạt. Không gửi goal mới khi kiểm tra giao diện.

Điều chỉnh theo phản hồi tiếp theo: giữ giao diện RViz quen thuộc với nền xám, lưới mét, occupancy map đen/trắng; LiDAR đỏ và footprint bật mặc định ngoài nhóm Diagnostics. RobotModel đọc `/robot_description` với QoS transient-local để hiển thị TurtleBot 4 thật, thay biểu tượng tròn tự vẽ. Nhãn/điểm đích được thu nhỏ; lớp tô vùng tắt mặc định nhưng có thể bật trong Namespaces. Node map_markers còn 15 marker. Kiểm tra subscriber trực tiếp nhận 281 bản quét trong khoảng 6 giây, mỗi bản có 640 tia, frame `turtlebot4/rplidar_link/rplidar`; nhận được robot_description. RViz hiển thị LiDAR Status OK, Global Status OK và mô hình robot; Navigation/Localization active. `rviz.png` là ảnh phiên bản mới nhất. Chỉ nạp lại các tiến trình hiển thị, không khởi động lại Gazebo/Nav2 và không gửi goal mới.
