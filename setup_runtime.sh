#!/usr/bin/env bash
# Build an isolated, pinned Humble TF2 runtime for Nav2 compatibility.
set -e
b7_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
b7_runtime="$b7_root/.runtime"
b7_revision=65c620c308920f558c7b5d3fb852941bd6d8fced
if [[ -f "$b7_runtime/install/tf2_ros/lib/libtf2_ros.so" ]]; then
    echo 'B7 TF2 runtime is ready.'
    exit 0
fi
mkdir -p "$b7_runtime/src"
if [[ ! -d "$b7_runtime/src/geometry2/.git" ]]; then
    git clone --depth 1 --branch 0.25.22 https://github.com/ros2/geometry2.git "$b7_runtime/src/geometry2"
fi
[[ $(git -C "$b7_runtime/src/geometry2" rev-parse HEAD) == "$b7_revision" ]]
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
CMAKE_BUILD_PARALLEL_LEVEL=4 colcon build \
    --base-paths "$b7_runtime/src/geometry2/tf2_ros" \
    --build-base "$b7_runtime/build" --install-base "$b7_runtime/install" \
    --packages-select tf2_ros --allow-overriding tf2_ros \
    --cmake-args -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release
