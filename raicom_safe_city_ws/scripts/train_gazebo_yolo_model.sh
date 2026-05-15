#!/usr/bin/env bash
set -euo pipefail

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${WS}/scripts/use_safe_city_env.sh"

DATA_FILE="${1:-${WS}/datasets/safe_city_formal_yolo/data.yaml}"
BASE_MODEL="${BASE_MODEL:-${WS}/models/safe_city_yolo.pt}"
if [[ ! -f "${BASE_MODEL}" ]]; then
  BASE_MODEL="${WS}/yolo11n.pt"
fi

EPOCHS="${EPOCHS:-45}"
IMGSZ="${IMGSZ:-640}"
RUN_NAME="${RUN_NAME:-safe_city_yolo_gazebo}"
YOLO_PYTHON="${YOLO_PYTHON:-${WS}/../tools/X-AnyLabeling/.venv-cpu/bin/python}"
if [[ ! -x "${YOLO_PYTHON}" ]]; then
  YOLO_PYTHON="/usr/bin/python3"
fi

PYTHONNOUSERSITE=1 "${YOLO_PYTHON}" - <<PY
from ultralytics import YOLO

model = YOLO("${BASE_MODEL}")
model.train(
    data="${DATA_FILE}",
    epochs=int("${EPOCHS}"),
    imgsz=int("${IMGSZ}"),
    name="${RUN_NAME}",
    project="${WS}/runs/detect",
    exist_ok=True,
)
PY

mkdir -p "${WS}/models"
cp "${WS}/runs/detect/${RUN_NAME}/weights/best.pt" "${WS}/models/safe_city_yolo.pt"
echo "Copied Gazebo-tuned YOLO model to ${WS}/models/safe_city_yolo.pt"
