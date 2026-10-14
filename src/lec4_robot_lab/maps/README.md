Để SLAM Toolbox vẫn chạy sau khi khảo sát. Xác nhận đang nhận được map, rồi lưu:

```bash
source ./lab_env.bash
ros2 topic info /map
timeout 10s ros2 topic echo /map --once >/dev/null || { echo 'Chua nhan duoc /map; de SLAM chay va thu lai.'; exit 1; }
ros2 run nav2_map_server map_saver_cli -f "$LEC4_WS/src/lec4_robot_lab/maps/map"
```

Lệnh phải báo `Map saved successfully`. `Failed to spin map subscription` nghĩa là map_saver chưa nhận được OccupancyGrid từ `/map`; giữ SLAM chạy, kiểm tra publisher rồi thử lại. Hai tệp kết quả là `map.yaml` và `map.pgm`.
