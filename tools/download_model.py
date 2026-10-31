#!/usr/bin/env python3
"""Download the full Whisper large-v3 model into this submission folder."""
from pathlib import Path
from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parents[1]
path = snapshot_download(
    'Systran/faster-whisper-large-v3', revision='edaa852ec7e145841d8ffdb056a99866b5f0a478',
    local_dir=root / 'models/whisper-large-v3',
    allow_patterns=['model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json',
                    'preprocessor_config.json', 'README.md'],
)
print('Model:', path)
