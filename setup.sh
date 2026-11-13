#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source ./b8_env.bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --timeout 120 -r requirements.txt
PYTHONPATH="$PWD/src/b8_emotion_control:$PYTHONPATH" .venv/bin/python -m b8_emotion_control.recognition
colcon build --base-paths src --packages-select b8_emotion_control --symlink-install
echo 'Da build. Chay: source ./b8_env.bash'
echo 'Sau do: ros2 launch b8_emotion_control emotion_demo.launch.py'
