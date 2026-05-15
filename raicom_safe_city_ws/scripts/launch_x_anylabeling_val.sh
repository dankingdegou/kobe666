#!/usr/bin/env bash
set -euo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${WS_DIR}/../tools/X-AnyLabeling"
XANY="${APP_DIR}/.venv-cpu/bin/xanylabeling"

if [[ ! -x "${XANY}" ]]; then
  echo "X-AnyLabeling is not installed at ${XANY}" >&2
  echo "Expected source directory: ${APP_DIR}" >&2
  exit 1
fi

if [[ "${XDG_SESSION_TYPE:-}" == "x11" ]] \
  && [[ ! -e /usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0 ]] \
  && [[ ! -e /lib/x86_64-linux-gnu/libxcb-cursor.so.0 ]]; then
  echo "Missing Qt X11 dependency: libxcb-cursor0." >&2
  echo "Install it once with: sudo apt-get install -y libxcb-cursor0" >&2
  exit 1
fi

PYTHONNOUSERSITE=1 XANYLABELING_MODEL_HUB="${XANYLABELING_MODEL_HUB:-modelscope}" "${XANY}" \
  --filename "${WS_DIR}/datasets/safe_city_yolo/images/val" \
  --output "${WS_DIR}/datasets/safe_city_yolo/labels/val" \
  --labels "${WS_DIR}/datasets/safe_city_yolo/classes.txt" \
  --validatelabel exact \
  --autosave \
  --nodata \
  --no-auto-update-check
