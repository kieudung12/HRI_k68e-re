#!/usr/bin/env bash
# Source the lec4 runtime (ROS domain, DDS, Gazebo and dependencies), then overlay B5.
if [[ -z "${BASH_VERSION:-}" ]]; then
    echo "LOI: hay dung bash de source b5_env.bash" >&2
    return 1
fi
export B5_WS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$B5_WS/../lec4/lab_env.bash" || return 1
if [[ -f "$B5_WS/install/setup.bash" ]]; then
    source "$B5_WS/install/setup.bash" || return 1
fi
export ROS_LOG_DIR="$B5_WS/log/ros"
mkdir -p "$ROS_LOG_DIR"
