#!/usr/bin/env python3
"""Use the same GPU model to inspect an audio file, without starting ROS."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/b7_voice_nav'))
from b7_voice_nav.whisper_engine import WhisperEngine

p = argparse.ArgumentParser()
p.add_argument('audio_file')
p.add_argument('--device', default='cuda')
p.add_argument('--compute-type', default='float16')
a = p.parse_args()
print(WhisperEngine(device=a.device, compute_type=a.compute_type).transcribe(a.audio_file))
