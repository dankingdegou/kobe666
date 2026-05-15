from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("safe_city_perception"),
        "config",
        "aruco_map.yaml",
    )

    publisher = Node(
        package="safe_city_perception",
        executable="test_image_publisher_node",
        output="screen",
    )

    detector = Node(
        package="safe_city_perception",
        executable="aruco_detector_node",
        output="screen",
        parameters=[{"aruco_map_file": config}],
    )

    reporter = Node(
        package="safe_city_perception",
        executable="result_reporter_node",
        output="screen",
    )

    return LaunchDescription([publisher, detector, reporter])
