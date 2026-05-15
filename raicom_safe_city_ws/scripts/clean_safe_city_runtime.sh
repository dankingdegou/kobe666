#!/usr/bin/env bash
set -euo pipefail

patterns=(
  "ros2 launch safe_city"
  "gz sim"
  "parameter_bridge"
  "map_server"
  "controller_server"
  "planner_server"
  "behavior_server"
  "bt_navigator"
  "waypoint_follower"
  "lifecycle_manager"
  "static_transform_publisher"
  "map_to_odom_tf"
  "base_to_lidar_tf"
  "base_footprint_to_base_link_tf"
  "aruco_detector_node"
  "result_reporter_node"
  "mission_coordinator_node"
  "patrol_nav_node"
  "competition_console.py"
)

for pattern in "${patterns[@]}"; do
  pids="$(pgrep -f "${pattern}" 2>/dev/null || true)"
  for pid in ${pids}; do
    if [[ "${pid}" != "$$" && "${pid}" != "${PPID}" ]]; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
done

sleep 1

for pattern in "${patterns[@]}"; do
  pids="$(pgrep -f "${pattern}" 2>/dev/null || true)"
  for pid in ${pids}; do
    if [[ "${pid}" != "$$" && "${pid}" != "${PPID}" ]]; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  done
done

echo "Safe City runtime processes cleaned."
