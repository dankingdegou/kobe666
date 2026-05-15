#!/usr/bin/env bash

export PYTHONNOUSERSITE=1

# VS Code installed from Snap injects SNAP_* runtime paths. Gazebo GUI can then
# pick Snap's glibc/pthread and crash with GLIBC_PRIVATE symbol errors.
unset SNAP SNAP_ARCH SNAP_COMMON SNAP_CONTEXT SNAP_COOKIE SNAP_DATA SNAP_EUID
unset SNAP_INSTANCE_NAME SNAP_LAUNCHER_ARCH_TRIPLET SNAP_LIBRARY_PATH SNAP_NAME
unset SNAP_REAL_HOME SNAP_REVISION SNAP_UID SNAP_USER_COMMON SNAP_USER_DATA SNAP_VERSION
unset LD_PRELOAD
unset GDK_PIXBUF_MODULEDIR GDK_PIXBUF_MODULE_FILE GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR
unset GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_PATH LOCPATH

export XDG_DATA_HOME="${HOME}/.local/share"
export XDG_DATA_DIRS="${XDG_DATA_DIRS_VSCODE_SNAP_ORIG:-/usr/share/ubuntu:/usr/share/gnome:/usr/local/share:/usr/share:/var/lib/snapd/desktop}"
export XDG_CONFIG_DIRS="${XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG:-/etc/xdg/xdg-ubuntu:/etc/xdg}"

SAFE_CITY_WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAFE_CITY_GAZEBO_SHARE="${SAFE_CITY_WS}/install/safe_city_gazebo/share/safe_city_gazebo"
export GZ_SIM_RESOURCE_PATH="${SAFE_CITY_GAZEBO_SHARE}:${SAFE_CITY_GAZEBO_SHARE}/models:${GZ_SIM_RESOURCE_PATH:-}"
export GAZEBO_MODEL_PATH="${SAFE_CITY_GAZEBO_SHARE}/models:${GAZEBO_MODEL_PATH:-}"

if shopt -qo nounset; then
  set +u
  source /opt/ros/jazzy/setup.bash
  source "${SAFE_CITY_WS}/install/setup.bash"
  set -u
else
  source /opt/ros/jazzy/setup.bash
  source "${SAFE_CITY_WS}/install/setup.bash"
fi
