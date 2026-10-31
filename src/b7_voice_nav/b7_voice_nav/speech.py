"""Press Enter, speak, then Enter again: microphone -> Whisper -> ROS text."""
import time

import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .whisper_engine import WhisperEngine, default_model_path


def record_sentence(device, max_seconds=15):
    import sounddevice as sd
    frames = []
    status_messages = []

    def capture(indata, frame_count, timing, status):
        if status:
            status_messages.append(str(status))
        # 100 ms blocks, bounded memory even if Enter is pressed much later.
        if len(frames) < max_seconds * 10:
            frames.append(indata.copy())

    with sd.InputStream(samplerate=16000, channels=1, dtype='float32',
                        device=device, blocksize=1600, callback=capture):
        input('DANG GHI - noi lenh, roi nhan Enter de ket thuc (toi da 15 giay): ')
    if status_messages:
        print('Trang thai am thanh:', ', '.join(set(status_messages)), flush=True)
    if not frames:
        return np.array([], dtype=np.float32)
    return np.concatenate(frames).reshape(-1)


def main():
    rclpy.init()
    node = Node('speech_recognition')
    node.declare_parameter('model_path', default_model_path())
    node.declare_parameter('device', 'pulse')
    node.declare_parameter('compute_device', 'cuda')
    node.declare_parameter('compute_type', 'float16')
    pub = node.create_publisher(String, '/voice_command', 10)
    try:
        import sounddevice as sd
        device = node.get_parameter('device').value or None
        selected = sd.query_devices(device, 'input')
        node.get_logger().info(f"Microphone: {selected['name']}")
        node.get_logger().info('Dang nap Whisper large-v3...')
        engine = WhisperEngine(
            node.get_parameter('model_path').value,
            node.get_parameter('compute_device').value,
            node.get_parameter('compute_type').value,
        )
        node.get_logger().info('Whisper san sang. Moi lan ghi mot cau lenh.')
        while rclpy.ok():
            input('\nNhan Enter de BAT DAU ghi: ')
            audio = record_sentence(device)
            if len(audio) < 4000:
                node.get_logger().warning('Ban ghi qua ngan. Hay noi lai.')
                continue
            rms = float(np.sqrt(np.mean(audio ** 2)))
            peak = float(np.max(np.abs(audio)))
            node.get_logger().info(f'Am luong RMS={rms:.4f}, peak={peak:.3f}')
            if rms < 0.002:
                node.get_logger().warning('Tin hieu qua nho: kiem tra Input trong Settings > Sound.')
                continue
            if np.mean(np.abs(audio) >= 0.99) > 0.01:
                node.get_logger().warning('Tin hieu bi meo: giam Input Volume cua microphone.')
            started = time.monotonic()
            text = engine.transcribe(audio)
            if not text:
                node.get_logger().warning('Khong tim thay loi noi. Hay thu lai.')
                continue
            node.get_logger().info(f'Nghe duoc ({time.monotonic()-started:.1f}s): {text}')
            # The navigation node validates the entire command, including unknown rooms.
            pub.publish(String(data=text))
            rclpy.spin_once(node, timeout_sec=0.1)
    except EOFError:
        node.get_logger().error('Hay chay lenh nay trong terminal tuong tac de nhan Enter.')
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        node.get_logger().error(str(exc))
        raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
