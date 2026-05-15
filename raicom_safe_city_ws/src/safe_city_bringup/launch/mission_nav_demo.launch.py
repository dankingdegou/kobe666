from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    perception_share = get_package_share_directory("safe_city_perception")
    navigation_share = get_package_share_directory("safe_city_navigation")

    camera_sim = os.path.join(
        get_package_share_directory("safe_city_gazebo"),
        "launch",
        "camera_sim.launch.py",
    )
    aruco_map = os.path.join(perception_share, "config", "aruco_map.yaml")
    zone_map = os.path.join(perception_share, "config", "zone_map.yaml")
    mission_plan = os.path.join(perception_share, "config", "mission_plan.yaml")
    waypoints = os.path.join(navigation_share, "config", "waypoints.yaml")

    return LaunchDescription(
        [
            IncludeLaunchDescription(PythonLaunchDescriptionSource(camera_sim)),
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
                executable="mission_coordinator_node",
                output="screen",
                parameters=[
                    {"mission_plan_file": mission_plan},
                    {"auto_trigger": False},
                ],
            ),
            Node(
                package="safe_city_perception",
                executable="patrol_trigger_node",
                output="screen",
                parameters=[
                    {"waypoints_file": waypoints},
                    {"mission_plan_file": mission_plan},
                    {"step_interval_sec": 4.0},
                ],
            ),
        ]
    )
