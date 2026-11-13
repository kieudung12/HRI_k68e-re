# Nguồn model và thư viện

- **DeepFace 0.0.104**: dò và căn chỉnh mặt; model Emotion dự phòng. [Mã nguồn và giấy phép MIT](https://github.com/serengil/deepface).
- **HSEmotion / EmotiEffLib, EfficientNet-B2, `enet_b2_7.onnx`**: model biểu cảm mặc định của Andrey Savchenko và cộng tác viên, huấn luyện cho 7 lớp biểu cảm. [Nguồn và giấy phép Apache-2.0](https://github.com/sb-ai-lab/EmotiEffLib). Không huấn luyện lại trong bài tập.
- [Tiền xử lý và thứ tự lớp của HSEmotion ONNX](https://github.com/av-savchenko/hsemotion-onnx/blob/main/hsemotion_onnx/facial_emotions.py): đầu vào RGB 260×260, chuẩn hóa theo ImageNet, đầu ra qua softmax. Bài này nạp trực tiếp bằng ONNX Runtime đang có, không cài thêm framework học sâu.

Model HSEmotion được khóa tại revision `520a051c64cd191521e5934655314e769a319684`:

[Tải model từ nguồn đã khóa](https://raw.githubusercontent.com/sb-ai-lab/EmotiEffLib/520a051c64cd191521e5934655314e769a319684/models/affectnet_emotions/onnx/enet_b2_7.onnx).

SHA-256: `7863032d8c0c0bc259aa0dd7b8ebf6b607af454e7a0ea82be2b37767914ecd0f`.

`recognition.py` kiểm tra checksum trước khi dùng. Model tải vào `b8/models/`, được loại khỏi Git và không được nhúng vào mã nguồn. Xem giấy phép của nguồn model khi phân phối lại weights. Không dùng các điểm số trên vài ảnh demo để suy ra độ chính xác trên người dùng.

Ảnh giao diện trong `docs/webcam_ui.png` dùng [ảnh astronaut của scikit-image/NASA](https://github.com/scikit-image/scikit-image/blob/v0.24.0/skimage/data/astronaut.png) làm đầu vào minh họa, không phải ảnh riêng của người dùng.
