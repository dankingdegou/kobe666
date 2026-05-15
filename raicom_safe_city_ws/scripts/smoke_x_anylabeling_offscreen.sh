#!/usr/bin/env bash
set -euo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${WS_DIR}/../tools/X-AnyLabeling"
XANY="${APP_DIR}/.venv-cpu/bin/xanylabeling"

if [[ ! -x "${XANY}" ]]; then
  echo "X-AnyLabeling is not installed at ${XANY}" >&2
  exit 1
fi

QT_QPA_PLATFORM=offscreen timeout 5 "${XANY}" \
  --filename "${WS_DIR}/datasets/safe_city_yolo/images/train" \
  --output "${WS_DIR}/datasets/safe_city_yolo/labels/train" \
  --labels "${WS_DIR}/datasets/safe_city_yolo/classes.txt" \
  --validatelabel exact \
  --autosave \
  --nodata \
  --no-auto-update-check || status=$?

status="${status:-0}"
if [[ "${status}" == "124" ]]; then
  echo "X-AnyLabeling offscreen smoke test reached GUI event loop."
  exit 0
fi
exit "${status}"
