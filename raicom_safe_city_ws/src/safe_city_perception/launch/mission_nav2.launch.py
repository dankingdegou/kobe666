from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    perception_share = get_package_share_directory("safe_city_perception")
    navigation_share = get_package_share_directory("safe_city_navigation")

    yolo_config = os.path.join(perception_share, "config", "yolo_classes.yaml")
    zone_map = os.path.join(perception_share, "config", "zone_map.yaml")
    mission_plan = os.path.join(perception_share, "config", "mission_plan.yaml")
    waypoints = os.path.join(navigation_share, "config", "waypoints.yaml")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "yolo_model",
                default_value="",
                description="Optional YOLO model path. Empty uses yolo_classes.yaml default.",
            ),
            DeclareLaunchArgument(
                "clean_output",
                default_value="false",
                description="Print only task recognition reports from result_reporter_node.",
            ),
            Node(
                package="safe_city_perception",
                executable="yolo_detector_node",
                output="log",
                parameters=[
                    {"yolo_config_file": yolo_config},
                    {"model_path": LaunchConfiguration("yolo_model")},
                    {"image_topic": "/camera"},
                    {"publish_every_n_frames": 2},
                ],
            ),
            Node(
                package="safe_city_perception",
                executable="result_reporter_node",
                output="screen",
                parameters=[
                    {"zone_map_file": zone_map},
                    {"memory_window_sec": 120.0},
                    {"clean_output": LaunchConfiguration("clean_output")},
                ],
            ),
            Node(
                package="safe_city_perception",
                executable="mission_coordinator_node",
                output="log",
                parameters=[
                    {"mission_plan_file": mission_plan},
                    {"auto_trigger": False},
                ],
            ),
            Node(
                package="safe_city_perception",
                executable="patrol_nav_node",
                output="log",
                parameters=[
                    {"waypoints_file": waypoints},
                    {"mission_plan_file": mission_plan},
                    {"simulate_navigation": False},
                    {"simple_navigation": True},
                    {"step_interval_sec": 1.2},
                    {"nav_timeout_sec": 55.0},
                    {"startup_delay_sec": 8.0},
                ],
            ),
        ]
    )
