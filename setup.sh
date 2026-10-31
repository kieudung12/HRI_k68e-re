#!/usr/bin/env bash
# Run once after installing Ubuntu/ROS dependencies listed in README.
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ -f /opt/ros/humble/setup.bash ]] || { echo 'Can ROS 2 Humble trong /opt/ros/humble'; exit 1; }
python3 -m venv --system-site-packages .venv
PYTHONNOUSERSITE=1 .venv/bin/python -m pip install -r requirements.txt
bash setup_runtime.sh
source ./b7_env.bash
colcon build --base-paths src --packages-select b7_voice_nav --symlink-install
source ./b7_env.bash
HF_HUB_DISABLE_XET=1 .venv/bin/python tools/download_model.py
ros2 run b7_voice_nav segment_map --output regions.png
echo 'B7 san sang. Moi terminal: source ./b7_env.bash'
