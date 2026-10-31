"""Whisper large-v3 inference; independent of ROS and microphone capture."""
import os
from pathlib import Path


def default_model_path():
    root = os.environ.get('B7_WS', str(Path(__file__).resolve().parents[3]))
    return os.environ.get('B7_WHISPER_MODEL', str(Path(root) / 'models/whisper-large-v3'))


class WhisperEngine:
    def __init__(self, model_path=None, device='cuda', compute_type='float16'):
        from faster_whisper import WhisperModel
        path = Path(model_path or default_model_path()).expanduser()
        if not (path / 'model.bin').is_file():
            raise FileNotFoundError(f'Chua co model tai {path}. Chay: bash setup.sh')
        prompt_path = Path(__file__).parent / 'prompts/whisper_vi.txt'
        self.initial_prompt = prompt_path.read_text(encoding='utf-8').strip()
        self.model = WhisperModel(str(path), device=device, compute_type=compute_type)

    def transcribe(self, audio):
        # Fixed Vietnamese language and a short context help with room names.
        segments, _ = self.model.transcribe(
            audio, language='vi', beam_size=5, temperature=0,
            condition_on_previous_text=False, vad_filter=True,
            vad_parameters={'min_silence_duration_ms': 400},
            initial_prompt=self.initial_prompt,
        )
        return ' '.join(segment.text.strip() for segment in segments).strip()
