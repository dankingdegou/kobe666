from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory("safe_city_perception")
    aruco_map = os.path.join(pkg_share, "config", "aruco_map.yaml")
    zone_map = os.path.join(pkg_share, "config", "zone_map.yaml")

    return LaunchDescription(
        [
            Node(
                package="safe_city_perception",
                executable="aruco_detector_node",
                output="screen",
                parameters=[
                    {"aruco_map_file": aruco_map},
                    {"image_topic": "/camera"},
                ],
            ),
            Node(
                package="safe_city_perception",
                executable="result_reporter_node",
                output="screen",
                parameters=[{"zone_map_file": zone_map}],
            ),
            Node(
                package="safe_city_perception",
                executable="zone_trigger_demo_node",
                output="screen",
            ),
        ]
    )
