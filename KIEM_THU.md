# Kết quả kiểm tra B8

Môi trường: Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, TurtleBot 4 Lite, Python 3.10. Cấu hình mặc định dùng DeepFace/OpenCV dò mặt và HSEmotion EfficientNet-B2 suy luận bằng ONNX Runtime trên CPU.

## 1. Build và kiểm thử logic

```bash
colcon build --base-paths src --packages-select b8_emotion_control --symlink-install
PYTHONPATH=src/b8_emotion_control python3 -m unittest discover \
  -s src/b8_emotion_control/test -v
```

Kết quả: build thành công, **21/21 kiểm thử qua**. Các trường hợp gồm ánh xạ vận tốc, Neutral dừng, hành động ngắn không lặp, khôi phục cung tròn sau mất mặt, EMA/chuyển nhãn, giới hạn tín hiệu, tích lũy vòng xoay qua biên yaw và hiệu chỉnh Neutral.

## 2. World trống và chuyển động

World `b8_empty` chỉ chứa mặt sàn và ánh sáng; khi robot được spawn, dữ liệu scene xác nhận hai model `ground_plane` và `turtlebot4`. Không có tường, đồ vật hay vật cản. Camera Follow và offset trả kết quả thành công; góc nhìn gần robot như [ảnh kiểm tra](docs/empty_world.png).

Lượt kiểm tra trực tiếp `/cmd_vel` và đo `/odom` trong sân trống:

| Lệnh | Quãng đường đo được | Thay đổi yaw | Kết quả |
| --- | ---: | ---: | --- |
| Tiến `v=0.12`, `ω=0` trong 1,8 giây | 0,216 m | gần 0 rad | Qua |
| Cong trái `v=0.12`, `ω=0.35` trong 1,8 giây | 0,212 m | +0,630 rad | Qua |
| Cong phải `v=0.12`, `ω=-0.35` trong 1,8 giây | 0,212 m | −0,629 rad | Qua |

Các phép đo này kiểm tra mô phỏng và hướng chuyển động, không đánh giá độ chính xác nhận diện biểu cảm.

## 3. Hiệu chỉnh Neutral và giao diện

Kiểm tra hồi quy bằng GUI, controller ROS và **điểm phân loại giả lập**, không giả nhận đây là đo trên mặt người dùng:

- Mới mở mà chưa lấy mẫu: chỉ gửi `NONE`, vận tốc bằng 0 dù điểm model nghiêng về Sad.
- Khi lấy mẫu, robot dừng và Space không bật lại điều khiển giữa quá trình.
- Mẫu thả lỏng bị model nghiêng về Sad 70%: sau hiệu chỉnh được chọn Neutral và dừng.
- Tăng Sad từ mẫu 70% lên 95%: vẫn chọn Sad và tạo cung phải; trở về mẫu chuẩn thì dừng.
- Mất mặt: dừng; mẫu cũ không tạo lệnh thay thế cho khuôn mặt đang mất.
- Người dùng đã tạm dừng trước hiệu chỉnh: giữ tạm dừng sau khi hoàn tất.
- Xóa mẫu: giữ robot dừng và yêu cầu lấy mẫu lại.

Đã kiểm tra thao tác trên thanh ngưỡng, thẻ gợi ý, nút tạm dừng/tiếp tục và đóng camera. Thẻ gợi ý không tự phát lệnh biểu cảm.

## 4. Chạy toàn bộ hệ thống

Đã chạy đúng lệnh launch mặc định với webcam thật và sân trống. Trong lượt khởi động chưa hiệu chỉnh, tất cả nhãn phát ra là `NONE`, tất cả `Twist` bằng 0; nhận được 714 mẫu odometry và độ dịch chuyển khởi động gần 0. Ctrl+C kết thúc sạch các node và simulator.

Các lượt kiểm tra model thật trước đó nhận được Happy/Neutral trên ảnh mẫu công khai và truyền lệnh tới controller. Các điểm dự đoán trên vài ảnh không phải độ chính xác trên một tập kiểm thử.

## 5. Giới hạn

- Chưa đánh giá đủ 6 biểu cảm của người dùng thật theo nhãn đối chiếu; chưa có ma trận nhầm lẫn hoặc tỷ lệ chính xác cá nhân.
- Hiệu chỉnh Neutral là xử lý sau model, không huấn luyện lại. Cần lấy mẫu khi thả lỏng mặt, với ánh sáng và góc nhìn của phiên demo.
- Đã kiểm tra mô phỏng, chưa chạy trên TurtleBot vật lý. Bộ dò RetinaFace là tùy chọn, không dùng trong các phép đo mặc định trên.
- Log chi tiết được giữ tại `log/` trên máy phát triển; không đưa log, ảnh webcam riêng, model hoặc môi trường Python lên Git.
