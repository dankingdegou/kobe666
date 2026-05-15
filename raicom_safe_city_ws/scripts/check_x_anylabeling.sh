#!/usr/bin/env bash
set -euo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${WS_DIR}/../tools/X-AnyLabeling"
XANY="${APP_DIR}/.venv-cpu/bin/xanylabeling"

if [[ ! -x "${XANY}" ]]; then
  echo "X-AnyLabeling is not installed at ${XANY}" >&2
  exit 1
fi

PYTHONNOUSERSITE=1 "${XANY}" checks
