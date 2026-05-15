#!/usr/bin/env python3
import math
import pathlib

from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
import yaml


class PatrolExecutorNode(Node):
    def __init__(self):
        super().__init__("patrol_executor_node")
        print("patrol_executor: init start", flush=True)
        ws_root = pathlib.Path(__file__).resolve().parents[2]
        default_waypoints = ws_root / "safe_city_navigation" / "config" / "waypoints.yaml"
        default_plan = ws_root / "safe_city_perception" / "config" / "mission_plan.yaml"

        self.declare_parameter("waypoints_file", str(default_waypoints))
        self.declare_parameter("mission_plan_file", str(default_plan))
        self.declare_parameter("trigger_topic", "/safe_city/task/zone_trigger")
        self.declare_parameter("state_topic", "/safe_city/task/patrol_state")
        self.declare_parameter("simulate_navigation", True)
        self.declare_parameter("step_interval_sec", 5.0)

        self.trigger_topic = self.get_parameter("trigger_topic").value
        self.state_topic = self.get_parameter("state_topic").value
        self.simulate_navigation = bool(self.get_parameter("simulate_navigation").value)
        self.step_interval_sec = float(self.get_parameter("step_interval_sec").value)
        self.waypoints = self._load_waypoints(
            self.get_parameter("waypoints_file").get_parameter_value().string_value
        )
        self.mission = self._load_mission(
            self.get_parameter("mission_plan_file").get_parameter_value().string_value
        )

        self.ordered_zones = self.mission.get("ordered_zones", [])
        self.zone_to_waypoint = self.mission.get("zone_to_waypoint", {})
        self.index = 0

        self.trigger_pub = self.create_publisher(String, self.trigger_topic, 10)
        self.state_pub = self.create_publisher(String, self.state_topic, 10)
        self.nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.timer = self.create_timer(self.step_interval_sec, self._tick)

        self.get_logger().info("Patrol executor ready.")
        self.get_logger().info(f"Simulate navigation: {self.simulate_navigation}")
        self.get_logger().info(f"Ordered zones: {self.ordered_zones}")
        print("patrol_executor: init done", flush=True)

    def _load_waypoints(self, path_str):
        path = pathlib.Path(path_str)
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        points = data.get("waypoints", {}).get("ros__parameters", {}).get("points", [])
        return {item["name"]: item for item in points}

    def _load_mission(self, path_str):
        path = pathlib.Path(path_str)
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data.get("mission", {})

    def _tick(self):
        print(f"patrol_executor: tick index={self.index}", flush=True)
        if self.index >= len(self.ordered_zones):
            self.get_logger().info("Patrol executor finished all zones.")
            self.timer.cancel()
            return

        zone = self.ordered_zones[self.index]
        waypoint_name = self.zone_to_waypoint.get(zone, zone)
        waypoint = self.waypoints.get(waypoint_name)
        if waypoint is None:
            self.get_logger().warn(f"Waypoint not found for zone {zone}: {waypoint_name}")
            self.index += 1
            return

        self._publish_state(f"navigating:{zone}:{waypoint_name}")
        if self.simulate_navigation:
            self.get_logger().info(f"[PATROL] Simulated arrival at {zone} via {waypoint_name}")
            self._trigger_zone(zone)
            self.index += 1
            return

        self._send_nav_goal(zone, waypoint)
        self.index += 1

    def _trigger_zone(self, zone):
        msg = String()
        msg.data = zone
        self.trigger_pub.publish(msg)
        self._publish_state(f"triggered:{zone}")

    def _publish_state(self, state):
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)

    def _send_nav_goal(self, zone, waypoint):
        if not self.nav_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("NavigateToPose action server not available.")
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._to_pose_stamped(waypoint)
        send_future = self.nav_client.send_goal_async(goal_msg)
        send_future.add_done_callback(
            lambda future, zone_name=zone: self._goal_response_callback(future, zone_name)
        )

    def _goal_response_callback(self, future, zone):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn(f"[PATROL] Goal rejected for zone {zone}")
            return
        self.get_logger().info(f"[PATROL] Goal accepted for zone {zone}")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda future, zone_name=zone: self._goal_result_callback(future, zone_name)
        )

    def _goal_result_callback(self, future, zone):
        self.get_logger().info(f"[PATROL] Arrived at zone {zone}")
        self._trigger_zone(zone)

    def _to_pose_stamped(self, waypoint):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(waypoint["x"])
        pose.pose.position.y = float(waypoint["y"])
        pose.pose.position.z = 0.0
        pose.pose.orientation = self._yaw_to_quaternion(float(waypoint["yaw"]))
        return pose

    def _yaw_to_quaternion(self, yaw):
        q = Quaternion()
        q.z = math.sin(yaw * 0.5)
        q.w = math.cos(yaw * 0.5)
        return q


def main():
    print("patrol_executor: main enter", flush=True)
    rclpy.init()
    node = PatrolExecutorNode()
    try:
        print("patrol_executor: spinning", flush=True)
        rclpy.spin(node)
    finally:
        print("patrol_executor: shutdown", flush=True)
        node.destroy_node()
        rclpy.shutdown()
