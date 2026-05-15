from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    publisher = Node(
        package="safe_city_perception",
        executable="test_image_publisher_node",
        output="screen",
    )

    mock_detector = Node(
        package="safe_city_perception",
        executable="mock_detection_publisher_node",
        output="screen",
    )

    reporter = Node(
        package="safe_city_perception",
        executable="result_reporter_node",
        output="screen",
    )

    return LaunchDescription([publisher, mock_detector, reporter])
