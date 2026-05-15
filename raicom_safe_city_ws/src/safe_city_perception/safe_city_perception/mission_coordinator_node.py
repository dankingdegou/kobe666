import json
import pathlib

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import yaml


class MissionCoordinatorNode(Node):
    def __init__(self):
        super().__init__("mission_coordinator_node")
        default_plan = (
            pathlib.Path(__file__).resolve().parents[1] / "config" / "mission_plan.yaml"
        )
        self.declare_parameter("mission_plan_file", str(default_plan))
        self.declare_parameter("trigger_topic", "/safe_city/task/zone_trigger")
        self.declare_parameter("report_topic", "/safe_city/task/zone_report")
        self.declare_parameter("auto_trigger", True)

        plan_file = self.get_parameter("mission_plan_file").get_parameter_value().string_value
        self.trigger_topic = self.get_parameter("trigger_topic").value
        self.report_topic = self.get_parameter("report_topic").value
        self.auto_trigger = bool(self.get_parameter("auto_trigger").value)

        mission_cfg = self._load_plan(plan_file)
        self.ordered_zones = mission_cfg.get("ordered_zones", [])
        self.trigger_interval_sec = float(mission_cfg.get("trigger_interval_sec", 4.0))
        self.report_timeout_sec = float(mission_cfg.get("report_timeout_sec", 2.5))

        self.zone_index = 0
        self.pending_zone = None
        self.completed = {}

        self.trigger_pub = self.create_publisher(String, self.trigger_topic, 10)
        self.report_sub = self.create_subscription(
            String, self.report_topic, self._report_callback, 10
        )
        self.trigger_sub = self.create_subscription(
            String, self.trigger_topic, self._external_trigger_callback, 10
        )
        self.timer = None
        if self.auto_trigger:
            self.timer = self.create_timer(self.trigger_interval_sec, self._tick)

        self.get_logger().info("Mission coordinator ready.")
        self.get_logger().info(f"Ordered zones: {self.ordered_zones}")
        self.get_logger().info(f"Auto trigger: {self.auto_trigger}")

    def _load_plan(self, path_str):
        path = pathlib.Path(path_str)
        if not path.exists():
            self.get_logger().warn(f"Mission plan file not found: {path}")
            return {}
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data.get("mission", {})

    def _tick(self):
        if self.pending_zone is not None:
            return
        if self.zone_index >= len(self.ordered_zones):
            self._print_mission_summary()
            self.timer.cancel()
            return

        zone = self.ordered_zones[self.zone_index]
        msg = String()
        msg.data = zone
        self.trigger_pub.publish(msg)
        self.pending_zone = zone
        self.zone_index += 1
        self.get_logger().info(f"[MISSION] Triggered zone: {zone}")

    def _external_trigger_callback(self, msg):
        if self.auto_trigger:
            return
        zone = msg.data.strip()
        if not zone:
            return
        self.pending_zone = zone
        self.get_logger().info(f"[MISSION] External trigger: {zone}")

    def _report_callback(self, msg):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warn(f"Invalid mission report payload: {exc}")
            return

        zone = payload.get("zone_name")
        if not zone:
            return
        self.completed[zone] = payload
        if zone == self.pending_zone:
            self.pending_zone = None

        display_name = payload.get("display_name", zone)
        summary = payload.get("summary", {})
        readable = []
        for group, items in summary.items():
            parts = [f"{name}: {count}" for name, count in sorted(items.items())]
            readable.append(f"{group}: {', '.join(parts)}")
        if not readable:
            readable.append("识别结果: 未检测到目标")
        self.get_logger().info(f"[MISSION] Completed {display_name}")
        for line in readable:
            self.get_logger().info(f"[MISSION] {line}")
        if not self.auto_trigger and self._all_zones_completed():
            self._print_mission_summary()

    def _print_mission_summary(self):
        self.get_logger().info("===== Safe City Mission Summary =====")
        if not self.completed:
            self.get_logger().info("No zone reports were collected.")
            return
        for zone in self.ordered_zones:
            payload = self.completed.get(zone)
            if payload is None:
                self.get_logger().info(f"{zone}: 未完成")
                continue
            display_name = payload.get("display_name", zone)
            summary = payload.get("summary", {})
            readable = []
            for group, items in summary.items():
                parts = [f"{name}: {count}" for name, count in sorted(items.items())]
                readable.append(f"{group}: {', '.join(parts)}")
            if not readable:
                readable.append("识别结果: 未检测到目标")
            self.get_logger().info(f"{display_name}")
            for line in readable:
                self.get_logger().info(f"  {line}")
        self.get_logger().info(
            "[MISSION] Requirement coverage: 4000mm x 4000mm PDF map, multi-point navigation, trash/person/building recognition reports."
        )

    def _all_zones_completed(self):
        return all(zone in self.completed for zone in self.ordered_zones)


def main():
    rclpy.init()
    node = MissionCoordinatorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
