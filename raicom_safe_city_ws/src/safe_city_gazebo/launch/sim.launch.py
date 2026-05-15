from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory("safe_city_gazebo")
    gz_launch = os.path.join(
        get_package_share_directory("ros_gz_sim"),
        "launch",
        "gz_sim.launch.py",
    )
    default_world = os.path.join(pkg_share, "worlds", "safe_city.world.sdf")

    world_arg = DeclareLaunchArgument(
        "world",
        default_value=default_world,
        description="Path to the Gazebo world file.",
    )
    gz_args_arg = DeclareLaunchArgument(
        "gz_args",
        default_value="-r",
        description="Extra Gazebo arguments. Default runs Gazebo with GUI.",
    )

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={
            "gz_args": [LaunchConfiguration("gz_args"), " ", LaunchConfiguration("world")]
        }.items(),
    )

    return LaunchDescription([world_arg, gz_args_arg, gz])
