#!/usr/bin/env bash
export B8_WS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$B8_WS/../lec4/lab_env.bash" || return 1
if [[ -f "$B8_WS/install/local_setup.bash" ]]; then
    source "$B8_WS/install/local_setup.bash" || return 1
fi
export ROS_LOG_DIR="$B8_WS/log/ros"
mkdir -p "$ROS_LOG_DIR"
