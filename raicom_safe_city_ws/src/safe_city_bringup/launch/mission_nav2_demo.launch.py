from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    camera_sim = os.path.join(
        get_package_share_directory("safe_city_gazebo"),
        "launch",
        "camera_sim.launch.py",
    )
    nav2_launch = os.path.join(
        get_package_share_directory("safe_city_navigation"),
        "launch",
        "nav2.launch.py",
    )
    mission_nav2 = os.path.join(
        get_package_share_directory("safe_city_perception"),
        "launch",
        "mission_nav2.launch.py",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gz_args",
                default_value="-r",
                description="Gazebo args; default runs Gazebo with GUI. Use '-r -s' for headless server-only.",
            ),
            DeclareLaunchArgument(
                "clean_output",
                default_value="false",
                description="Only print task recognition reports in the terminal.",
            ),
            DeclareLaunchArgument(
                "log_level",
                default_value="info",
                description="ROS node log level for navigation stack.",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(camera_sim),
                launch_arguments={
                    "gz_args": LaunchConfiguration("gz_args"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_launch),
                launch_arguments={
                    "log_level": LaunchConfiguration("log_level"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(mission_nav2),
                launch_arguments={
                    "clean_output": LaunchConfiguration("clean_output"),
                }.items(),
            ),
        ]
    )
