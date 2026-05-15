cmake_minimum_required(VERSION 3.8)
project(safe_city_gazebo)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch worlds models materials
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
