from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory("safe_city_gazebo")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    world_file = os.path.join(pkg_share, "worlds", "safe_city.world.sdf")
    world_arg = DeclareLaunchArgument("world", default_value=world_file)
    gz_args_arg = DeclareLaunchArgument(
        "gz_args",
        default_value="-r",
        description="Extra Gazebo arguments. Default runs Gazebo with GUI.",
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": [LaunchConfiguration("gz_args"), " ", LaunchConfiguration("world")]
        }.items(),
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/camera@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
        ],
        output="log",
    )

    return LaunchDescription(
        [
            world_arg,
            gz_args_arg,
            gz_sim,
            bridge,
        ]
    )
