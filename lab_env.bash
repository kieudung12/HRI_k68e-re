# Source this file in each terminal; no user-specific path in source.
if [[ -z "${BASH_VERSION:-}" ]]; then
    echo "LOI: hay dung bash de source lab_env.bash" >&2
    return 1
fi
export LEC4_WS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH ROS_PACKAGE_PATH
unset IGN_GAZEBO_RESOURCE_PATH IGN_GUI_PLUGIN_PATH GAZEBO_MODEL_PATH
unset IGN_IP
# VS Code is installed as a Snap on this machine. Its GTK/GIO module paths can
# make native ROS GUI tools (RViz/Gazebo) load incompatible Snap libraries.
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_MODULES
unset GDK_PIXBUF_MODULEDIR GDK_PIXBUF_MODULE_FILE GIO_MODULE_DIR GIO_EXTRA_MODULES
unset GIO_LAUNCHED_DESKTOP_FILE GIO_LAUNCHED_DESKTOP_FILE_PID
source /opt/ros/humble/setup.bash || return 1
if [[ -f "$LEC4_WS/install/setup.bash" ]]; then
    source "$LEC4_WS/install/setup.bash" || return 1
fi
if [[ -f "$LEC4_WS/.runtime/install/local_setup.bash" ]]; then
    source "$LEC4_WS/.runtime/install/local_setup.bash" || return 1
fi
export ROS_DOMAIN_ID=92
export ROS_LOCALHOST_ONLY=1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export RMW_FASTRTPS_PUBLICATION_MODE=ASYNCHRONOUS
export RMW_FASTRTPS_USE_QOS_FROM_XML=0
unset CYCLONEDDS_URI
# Use one UDP transport for all lab nodes. In runtime tests the default
# shared-memory transport left some long-lived TF readers stuck on old data.
export FASTRTPS_DEFAULT_PROFILES_FILE="$LEC4_WS/src/lec4_robot_lab/config/fastdds_udp.xml"
export IGN_PARTITION=lec4_robot_lab_92
# This lab runs Gazebo and ROS on one machine. Bind Ignition Transport to
# loopback so it does not advertise on unavailable external interfaces.
export IGN_IP=127.0.0.1
if [[ -f /proc/driver/nvidia/version ]]; then
    export __NV_PRIME_RENDER_OFFLOAD=1
    export __GLX_VENDOR_LIBRARY_NAME=nvidia
fi
export ROS_LOG_DIR="$LEC4_WS/log/ros"
mkdir -p "$ROS_LOG_DIR" "$LEC4_WS/evidence"
