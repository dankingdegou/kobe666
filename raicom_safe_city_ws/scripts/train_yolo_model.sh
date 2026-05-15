#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DATA_FILE="${1:-${WS_DIR}/datasets/safe_city_yolo/data.yaml}"
BASE_MODEL="${BASE_MODEL:-yolo11n.pt}"
EPOCHS="${EPOCHS:-80}"
IMGSZ="${IMGSZ:-640}"
RUN_NAME="${RUN_NAME:-safe_city_yolo}"

export PYTHONNOUSERSITE="${PYTHONNOUSERSITE:-1}"

python3 - <<'PY'
try:
    import ultralytics  # noqa: F401
except ImportError as exc:
    raise SystemExit(
        "ultralytics is not installed. Install it in the Python environment used for "
        "training, then rerun this script. Original error: " + str(exc)
    )
PY

yolo detect train \
  model="${BASE_MODEL}" \
  data="${DATA_FILE}" \
  epochs="${EPOCHS}" \
  imgsz="${IMGSZ}" \
  name="${RUN_NAME}" \
  project="${WS_DIR}/runs/detect"

mkdir -p "${WS_DIR}/models"
BEST_MODEL="${WS_DIR}/runs/detect/${RUN_NAME}/weights/best.pt"
if [[ -f "${BEST_MODEL}" ]]; then
  cp "${BEST_MODEL}" "${WS_DIR}/models/safe_city_yolo.pt"
  echo "Copied best model to ${WS_DIR}/models/safe_city_yolo.pt"
else
  echo "Training finished, but best.pt was not found at ${BEST_MODEL}" >&2
fi
