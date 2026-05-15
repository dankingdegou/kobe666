#!/usr/bin/env bash
set -euo pipefail

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${WS}/scripts/use_safe_city_env.sh"

if [[ -x "${WS}/scripts/clean_safe_city_runtime.sh" ]]; then
  bash "${WS}/scripts/clean_safe_city_runtime.sh" >/dev/null 2>&1 || true
fi

LOG_DIR="${WS}/log/competition_demo"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/$(date +%Y%m%d_%H%M%S).log"
GZ_ARGS="${SAFE_CITY_GZ_ARGS:--r}"
LAUNCH_PID=""

launch_alive() {
  [[ -n "${LAUNCH_PID}" ]] || return 1
  kill -0 "${LAUNCH_PID}" >/dev/null 2>&1 || return 1
  local state
  state="$(ps -o stat= -p "${LAUNCH_PID}" 2>/dev/null | tr -d ' ')"
  [[ "${state}" != Z* ]]
}

stop_launch() {
  launch_alive || return 0
  kill -INT "-${LAUNCH_PID}" >/dev/null 2>&1 || kill -INT "${LAUNCH_PID}" >/dev/null 2>&1 || true
  for _ in {1..12}; do
    launch_alive || break
    sleep 0.5
  done
  if launch_alive; then
    kill -TERM "-${LAUNCH_PID}" >/dev/null 2>&1 || kill -TERM "${LAUNCH_PID}" >/dev/null 2>&1 || true
    for _ in {1..6}; do
      launch_alive || break
      sleep 0.5
    done
  fi
  if launch_alive; then
    kill -KILL "-${LAUNCH_PID}" >/dev/null 2>&1 || kill -KILL "${LAUNCH_PID}" >/dev/null 2>&1 || true
  fi
  wait "${LAUNCH_PID}" >/dev/null 2>&1 || true
}

cleanup() {
  stop_launch
  if [[ -x "${WS}/scripts/clean_safe_city_runtime.sh" ]]; then
    bash "${WS}/scripts/clean_safe_city_runtime.sh" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "RAICOM 平安城市干净演示模式"
echo "终端仅输出到达识别点后的识别结果；完整 ROS/Gazebo 日志保存在 ${LOG_FILE}"
echo

setsid ros2 launch safe_city_bringup mission_nav2_demo.launch.py \
  gz_args:="${GZ_ARGS}" \
  clean_output:=false \
  log_level:=error >"${LOG_FILE}" 2>&1 &
LAUNCH_PID="$!"

python3 "${WS}/scripts/competition_console.py"
