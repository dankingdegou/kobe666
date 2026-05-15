#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHONNOUSERSITE=1 /usr/bin/python3 scripts/prepare_yolo_dataset.py --bootstrap-full-box --val-all
PYTHONNOUSERSITE=1 /usr/bin/python3 scripts/export_yolo_labels.py

echo "Generated full-image YOLO boxes for a quick baseline."
echo "These labels are only for smoke testing. Refine them before formal training."
