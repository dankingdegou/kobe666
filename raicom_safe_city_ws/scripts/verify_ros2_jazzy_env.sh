#!/usr/bin/env bash
set -euo pipefail

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
else
  echo "ROS 2 Jazzy is not installed at /opt/ros/jazzy"
  exit 1
fi

echo "=== Core binaries ==="
command -v ros2
command -v gz
command -v colcon

echo
echo "=== ROS distro ==="
printenv ROS_DISTRO

echo
echo "=== Package checks ==="
ros2 pkg list | rg 'nav2|slam_toolbox|ros_gz|robot_state_publisher|rviz2' || true

echo
echo "=== Gazebo version ==="
gz sim --versions || true

echo
echo "Environment looks ready."
