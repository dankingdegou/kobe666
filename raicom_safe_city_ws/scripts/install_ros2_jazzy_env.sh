#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script with sudo:"
  echo "  sudo bash $0"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt update
apt install -y software-properties-common curl locales gnupg lsb-release ca-certificates

locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

add-apt-repository universe -y

apt update

ROS_APT_SOURCE_VERSION="$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | awk -F'\"' '/tag_name/{print $4}')"
UBUNTU_CODENAME="${UBUNTU_CODENAME:-$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")}"
DEB_PATH="/tmp/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"

curl -L -o "${DEB_PATH}" \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"

dpkg -i "${DEB_PATH}"

apt update
apt upgrade -y

apt install -y \
  ros-jazzy-desktop \
  ros-dev-tools \
  ros-jazzy-ros-gz \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-slam-toolbox \
  ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher-gui \
  ros-jazzy-tf2-tools \
  ros-jazzy-rviz2 \
  ros-jazzy-cv-bridge \
  ros-jazzy-image-transport \
  ros-jazzy-vision-opencv \
  python3-colcon-common-extensions \
  python3-opencv \
  python3-pip

ROS_SETUP='source /opt/ros/jazzy/setup.bash'
if ! grep -Fq "${ROS_SETUP}" /home/"${SUDO_USER:-$USER}"/.bashrc; then
  echo "${ROS_SETUP}" >> /home/"${SUDO_USER:-$USER}"/.bashrc
fi

echo
echo "ROS 2 Jazzy environment installation finished."
echo "Open a new shell or run: source /opt/ros/jazzy/setup.bash"
