from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os


def generate_launch_description():
    pkg_share = get_package_share_directory("safe_city_navigation")

    params_file = os.path.join(pkg_share, "config", "nav2_params.yaml")
    map_file = os.path.join(pkg_share, "maps", "safe_city_map.yaml")

    map_arg = DeclareLaunchArgument("map", default_value=map_file)
    params_arg = DeclareLaunchArgument("params_file", default_value=params_file)
    sim_time_arg = DeclareLaunchArgument("use_sim_time", default_value="true")
    autostart_arg = DeclareLaunchArgument("autostart", default_value="true")
    log_level_arg = DeclareLaunchArgument("log_level", default_value="info")

    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    map_yaml = LaunchConfiguration("map")
    params = LaunchConfiguration("params_file")
    log_level = LaunchConfiguration("log_level")

    remappings = [("/tf", "tf"), ("/tf_static", "tf_static")]

    common_args = ["--ros-args", "--log-level", log_level]

    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[params, {"use_sim_time": use_sim_time, "yaml_filename": map_yaml}],
        arguments=common_args,
        remappings=remappings,
    )

    map_to_odom_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="map_to_odom_tf",
        output="screen",
        arguments=["-1.35", "-1.35", "0", "0", "0", "0", "map", "odom"],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    base_link_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="base_footprint_to_base_link_tf",
        output="screen",
        arguments=[
            "0",
            "0",
            "0.01",
            "0",
            "0",
            "0",
            "base_footprint",
            "base_link",
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="base_to_lidar_tf",
        output="screen",
        arguments=[
            "-0.064",
            "0",
            "0.121",
            "0",
            "0",
            "0",
            "base_link",
            "base_scan",
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        output="screen",
        parameters=[params, {"use_sim_time": use_sim_time}],
        arguments=common_args,
        remappings=remappings,
    )

    planner_server = Node(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        output="screen",
        parameters=[params, {"use_sim_time": use_sim_time}],
        arguments=common_args,
        remappings=remappings,
    )

    behavior_server = Node(
        package="nav2_behaviors",
        executable="behavior_server",
        name="behavior_server",
        output="screen",
        parameters=[params, {"use_sim_time": use_sim_time}],
        arguments=common_args,
        remappings=remappings,
    )

    bt_navigator = Node(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        output="screen",
        parameters=[params, {"use_sim_time": use_sim_time}],
        arguments=common_args,
        remappings=remappings,
    )

    waypoint_follower = Node(
        package="nav2_waypoint_follower",
        executable="waypoint_follower",
        name="waypoint_follower",
        output="screen",
        parameters=[params, {"use_sim_time": use_sim_time}],
        arguments=common_args,
        remappings=remappings,
    )

    lifecycle_manager_localization = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"autostart": autostart},
            {"node_names": ["map_server"]},
        ],
        arguments=common_args,
    )

    lifecycle_manager_navigation = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"autostart": autostart},
            {
                "node_names": [
                    "controller_server",
                    "planner_server",
                    "behavior_server",
                    "bt_navigator",
                    "waypoint_follower",
                ]
            },
        ],
        arguments=common_args,
    )

    return LaunchDescription(
        [
            SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"),
            map_arg,
            params_arg,
            sim_time_arg,
            autostart_arg,
            log_level_arg,
            map_to_odom_tf,
            base_link_tf,
            lidar_tf,
            map_server,
            controller_server,
            planner_server,
            behavior_server,
            bt_navigator,
            waypoint_follower,
            lifecycle_manager_localization,
            lifecycle_manager_navigation,
        ]
    )
