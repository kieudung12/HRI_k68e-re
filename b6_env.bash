#!/usr/bin/env bash
# Load the shared TurtleBot 4 runtime from lec4, then the B6 overlay.
if [[ -z "${BASH_VERSION:-}" ]]; then
    echo "Loi: hay dung bash de source b6_env.bash" >&2
    return 1
fi
export B6_WS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$B6_WS/../lec4/lab_env.bash" || return 1
if [[ -f "$B6_WS/install/setup.bash" ]]; then
    source "$B6_WS/install/setup.bash" || return 1
fi
export ROS_LOG_DIR="$B6_WS/log/ros"
mkdir -p "$ROS_LOG_DIR"
