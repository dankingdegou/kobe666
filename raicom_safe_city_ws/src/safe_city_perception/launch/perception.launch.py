from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("safe_city_perception"),
        "config",
        "aruco_map.yaml",
    )
    yolo_config = os.path.join(
        get_package_share_directory("safe_city_perception"),
        "config",
        "yolo_classes.yaml",
    )

    model_arg = DeclareLaunchArgument(
        "yolo_model",
        default_value="",
        description="Optional YOLO model path. Empty uses yolo_classes.yaml default.",
    )

    detector = Node(
        package="safe_city_perception",
        executable="aruco_detector_node",
        output="screen",
        parameters=[{"aruco_map_file": config}],
    )

    yolo_detector = Node(
        package="safe_city_perception",
        executable="yolo_detector_node",
        output="screen",
        parameters=[
            {"yolo_config_file": yolo_config},
            {"model_path": LaunchConfiguration("yolo_model")},
        ],
    )

    reporter = Node(
        package="safe_city_perception",
        executable="result_reporter_node",
        output="screen",
    )

    return LaunchDescription([model_arg, yolo_detector, detector, reporter])
