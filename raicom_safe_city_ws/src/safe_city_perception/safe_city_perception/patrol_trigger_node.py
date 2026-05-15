import pathlib

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import yaml


class PatrolTriggerNode(Node):
    def __init__(self):
        super().__init__("patrol_trigger_node")
        ws_root = pathlib.Path(__file__).resolve().parents[3]
        default_waypoints = ws_root / "safe_city_navigation" / "config" / "waypoints.yaml"
        default_plan = ws_root / "safe_city_perception" / "config" / "mission_plan.yaml"

        self.declare_parameter("waypoints_file", str(default_waypoints))
        self.declare_parameter("mission_plan_file", str(default_plan))
        self.declare_parameter("trigger_topic", "/safe_city/task/zone_trigger")
        self.declare_parameter("state_topic", "/safe_city/task/patrol_state")
        self.declare_parameter("step_interval_sec", 4.0)

        self.trigger_topic = self.get_parameter("trigger_topic").value
        self.state_topic = self.get_parameter("state_topic").value
        self.step_interval_sec = float(self.get_parameter("step_interval_sec").value)

        self.waypoints = self._load_waypoints(
            self.get_parameter("waypoints_file").get_parameter_value().string_value
        )
        mission = self._load_mission(
            self.get_parameter("mission_plan_file").get_parameter_value().string_value
        )
        self.ordered_zones = mission.get("ordered_zones", [])
        self.zone_to_waypoint = mission.get("zone_to_waypoint", {})
        self.index = 0

        self.trigger_pub = self.create_publisher(String, self.trigger_topic, 10)
        self.state_pub = self.create_publisher(String, self.state_topic, 10)
        self.timer = self.create_timer(self.step_interval_sec, self._tick)

        self.get_logger().info("Patrol trigger node ready.")
        self.get_logger().info(f"Ordered zones: {self.ordered_zones}")

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
        if self.index >= len(self.ordered_zones):
            self.get_logger().info("Patrol trigger node finished all zones.")
            self.timer.cancel()
            return

        zone = self.ordered_zones[self.index]
        waypoint_name = self.zone_to_waypoint.get(zone, zone)
        waypoint = self.waypoints.get(waypoint_name)
        if waypoint is None:
            self.get_logger().warn(f"Waypoint not found for zone {zone}: {waypoint_name}")
            self.index += 1
            return

        self._publish_state(
            f"arrived:{zone}:{waypoint_name}:{waypoint['x']}:{waypoint['y']}:{waypoint['yaw']}"
        )
        trigger_msg = String()
        trigger_msg.data = zone
        self.trigger_pub.publish(trigger_msg)
        self.get_logger().info(f"[PATROL] Triggered {zone} via waypoint {waypoint_name}")
        self.index += 1

    def _publish_state(self, value):
        msg = String()
        msg.data = value
        self.state_pub.publish(msg)


def main():
    rclpy.init()
    node = PatrolTriggerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
