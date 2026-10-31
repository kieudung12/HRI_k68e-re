#!/usr/bin/env bash
# Source in each terminal. Only the ROS installation and this B7 folder are used.
if [[ -z "${BASH_VERSION:-}" ]]; then
    echo 'Hay source bang bash' >&2
    return 1
fi
export B7_WS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH ROS_PACKAGE_PATH
unset IGN_GAZEBO_RESOURCE_PATH IGN_GUI_PLUGIN_PATH IGN_GAZEBO_SYSTEM_PLUGIN_PATH
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_MODULES GDK_PIXBUF_MODULEDIR GDK_PIXBUF_MODULE_FILE GIO_MODULE_DIR GIO_EXTRA_MODULES
source /opt/ros/humble/setup.bash || return 1
if [[ -f "$B7_WS/.runtime/install/local_setup.bash" ]]; then
    source "$B7_WS/.runtime/install/local_setup.bash" || return 1
fi
if [[ -f "$B7_WS/install/local_setup.bash" ]]; then
    source "$B7_WS/install/local_setup.bash" || return 1
fi
export ROS_DOMAIN_ID=97
export ROS_LOCALHOST_ONLY=1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export RMW_FASTRTPS_PUBLICATION_MODE=SYNCHRONOUS
export RMW_FASTRTPS_USE_QOS_FROM_XML=0
export FASTRTPS_DEFAULT_PROFILES_FILE="$B7_WS/src/b7_voice_nav/config/fastdds_udp.xml"
unset CYCLONEDDS_URI
export IGN_PARTITION=b7_voice_nav_97
export IGN_IP=127.0.0.1
export ROS_LOG_DIR="$B7_WS/log/ros"
export PYTHONNOUSERSITE=1
export B7_WHISPER_MODEL="$B7_WS/models/whisper-large-v3"
if [[ -d "$B7_WS/.venv/lib/python3.10/site-packages" ]]; then
    b7_site="$B7_WS/.venv/lib/python3.10/site-packages"
    export PYTHONPATH="$b7_site:${PYTHONPATH:-}"
    export LD_LIBRARY_PATH="$b7_site/nvidia/cublas/lib:$b7_site/nvidia/cudnn/lib:${LD_LIBRARY_PATH:-}"
    unset b7_site
fi
if [[ -f /proc/driver/nvidia/version ]]; then
    export __NV_PRIME_RENDER_OFFLOAD=1
    export __GLX_VENDOR_LIBRARY_NAME=nvidia
fi
mkdir -p "$ROS_LOG_DIR"
