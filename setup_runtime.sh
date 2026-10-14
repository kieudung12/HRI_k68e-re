#!/usr/bin/env bash
# Build the official Humble TF2 ROS compatibility library in this workspace.
set -eo pipefail
lec4_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
lec4_runtime="$lec4_root/.runtime"
lec4_revision=65c620c308920f558c7b5d3fb852941bd6d8fced
if [[ -f "$lec4_runtime/install/tf2_ros/lib/libtf2_ros.so" &&
      -f "$lec4_runtime/revision" &&
      $(cat "$lec4_runtime/revision") == "$lec4_revision" ]]; then
    echo 'TF2 ROS 0.25.22 runtime already prepared.'
    exit 0
fi
mkdir -p "$lec4_runtime/src"
if [[ ! -d "$lec4_runtime/src/geometry2/.git" ]]; then
    git clone --depth 1 --branch 0.25.22 https://github.com/ros2/geometry2.git \
        "$lec4_runtime/src/geometry2"
fi
[[ $(git -C "$lec4_runtime/src/geometry2" rev-parse HEAD) == "$lec4_revision" ]] || {
    echo 'Unexpected geometry2 revision; refusing to build.' >&2
    exit 1
}
source /opt/ros/humble/setup.bash
CMAKE_BUILD_PARALLEL_LEVEL=4 colcon build \
    --base-paths "$lec4_runtime/src/geometry2/tf2_ros" \
    --build-base "$lec4_runtime/build" --install-base "$lec4_runtime/install" \
    --packages-select tf2_ros --allow-overriding tf2_ros \
    --cmake-args -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release
printf '%s\n' "$lec4_revision" > "$lec4_runtime/revision"
