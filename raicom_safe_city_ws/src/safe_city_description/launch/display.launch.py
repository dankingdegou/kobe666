from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory("safe_city_description")
    default_model = os.path.join(pkg_share, "urdf", "safe_city_robot.urdf.xacro")
    default_rviz = os.path.join(pkg_share, "rviz", "robot.rviz")

    model_arg = DeclareLaunchArgument(
        "model",
        default_value=default_model,
        description="Path to robot xacro file.",
    )

    robot_description = Command(["xacro ", LaunchConfiguration("model")])

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )

    jsp = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", default_rviz],
        output="screen",
    )

    return LaunchDescription([model_arg, jsp, rsp, rviz])
