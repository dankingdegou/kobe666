from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
import os


def generate_launch_description():
    sim_launch = os.path.join(
        get_package_share_directory("safe_city_gazebo"),
        "launch",
        "camera_sim.launch.py",
    )
    return LaunchDescription(
        [
            IncludeLaunchDescription(PythonLaunchDescriptionSource(sim_launch)),
            Node(
                package="safe_city_perception",
                executable="result_reporter_node",
                output="screen",
            ),
            Node(
                package="safe_city_perception",
                executable="mock_detection_publisher_node",
                output="screen",
            ),
        ]
    )
