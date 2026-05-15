from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    sim_launch = os.path.join(
        get_package_share_directory("safe_city_gazebo"),
        "launch",
        "sim.launch.py",
    )
    perception_launch = os.path.join(
        get_package_share_directory("safe_city_perception"),
        "launch",
        "perception.launch.py",
    )

    return LaunchDescription(
        [
            IncludeLaunchDescription(PythonLaunchDescriptionSource(sim_launch)),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(perception_launch)),
        ]
    )
