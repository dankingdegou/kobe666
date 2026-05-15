#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/sbin:${PATH:-}"
export AMENT_PYTHON_EXECUTABLE=/usr/bin/python3
export COLCON_PYTHON_EXECUTABLE=/usr/bin/python3
export PYTHONNOUSERSITE=1

if shopt -qo nounset; then
  set +u
  source /opt/ros/jazzy/setup.bash
  set -u
else
  source /opt/ros/jazzy/setup.bash
fi

cd "${WS_DIR}"
colcon build --symlink-install --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 "$@"
