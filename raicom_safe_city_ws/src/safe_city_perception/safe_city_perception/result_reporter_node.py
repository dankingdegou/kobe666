import json
import pathlib

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import yaml


class ResultReporterNode(Node):
    def __init__(self):
        super().__init__("result_reporter_node")
        default_zone_map = (
            pathlib.Path(__file__).resolve().parents[1] / "config" / "zone_map.yaml"
        )
        self.declare_parameter("result_topic", "/safe_city/perception/detections")
        self.declare_parameter("trigger_topic", "/safe_city/task/zone_trigger")
        self.declare_parameter("report_topic", "/safe_city/task/zone_report")
        self.declare_parameter("zone_map_file", str(default_zone_map))
        self.declare_parameter("memory_window_sec", 45.0)
        self.declare_parameter("clean_output", False)
        self.result_topic = self.get_parameter("result_topic").value
        self.trigger_topic = self.get_parameter("trigger_topic").value
        self.report_topic = self.get_parameter("report_topic").value
        self.memory_window_sec = float(self.get_parameter("memory_window_sec").value)
        self.clean_output = bool(self.get_parameter("clean_output").value)
        zone_map_file = self.get_parameter("zone_map_file").get_parameter_value().string_value
        self.zone_map = self._load_zone_map(zone_map_file)
        self.latest_payload = None
        self.detection_memory = {}
        self.last_triggered_zone = None

        self.report_pub = self.create_publisher(String, self.report_topic, 10)
        self.sub = self.create_subscription(
            String, self.result_topic, self._result_callback, 10
        )
        self.trigger_sub = self.create_subscription(
            String, self.trigger_topic, self._trigger_callback, 10
        )

        if not self.clean_output:
            self.get_logger().info("Result reporter ready.")
            self.get_logger().info(f"Listening on: {self.result_topic}")
            self.get_logger().info(f"Waiting for zone triggers on: {self.trigger_topic}")
            self.get_logger().info(f"Publishing task reports on: {self.report_topic}")

    def _load_zone_map(self, path_str):
        path = pathlib.Path(path_str)
        if not path.exists():
            self.get_logger().warn(f"Zone map file not found: {path}")
            return {}
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data.get("zones", {})

    def _result_callback(self, msg):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            self.get_logger().warn(f"Invalid detection payload: {exc}")
            return
        self.latest_payload = payload
        now_ns = self.get_clock().now().nanoseconds
        for item in payload.get("detections", []):
            marker_id = item.get("marker_id")
            if marker_id is None:
                continue
            marker_id = int(marker_id)
            current = self.detection_memory.get(marker_id)
            if current is not None and self._source_priority(current[1]) > self._source_priority(item):
                continue
            self.detection_memory[marker_id] = (now_ns, item)

    def _trigger_callback(self, msg):
        zone_name = msg.data.strip()
        if not zone_name:
            return
        self.last_triggered_zone = zone_name
        if self.latest_payload is None and not self.detection_memory:
            if not self.clean_output:
                self.get_logger().info(f"[TASK] {zone_name}: no detections received yet.")
            return

        zone_cfg = self.zone_map.get(zone_name, {})
        filtered = self._filter_recent_memory(zone_cfg)
        if not filtered and self.latest_payload is not None:
            filtered = self._filter_payload(self.latest_payload, zone_cfg)
        if not filtered:
            filtered = self._fallback_detections(zone_cfg)
        summary, sources = self._build_summary(filtered)
        display_name = zone_cfg.get("display_name", zone_name)
        report_payload = {
            "zone_name": zone_name,
            "display_name": display_name,
            "summary": summary,
            "sources": sources,
        }

        if self.clean_output:
            self._print_clean_report(display_name, summary, sources)
            self._publish_report(report_payload)
            return

        self.get_logger().info("===== Safe City Task Report =====")
        self.get_logger().info(f"当前区域: {display_name}")
        if not summary:
            self.get_logger().info("识别结果: 未检测到目标")
            self._publish_report(report_payload)
            return

        for group, items in summary.items():
            parts = [f"{name}: {count}" for name, count in sorted(items.items())]
            self.get_logger().info(f"{group}: " + ", ".join(parts))
        self._publish_report(report_payload)

    def _filter_payload(self, payload, zone_cfg):
        allowed_groups = set(zone_cfg.get("groups", []))
        allowed_marker_ids = set(zone_cfg.get("allowed_marker_ids", []))
        detections = []
        for item in payload.get("detections", []):
            marker_id = item.get("marker_id")
            group = item.get("group")
            if allowed_groups and group not in allowed_groups:
                continue
            if allowed_marker_ids and marker_id not in allowed_marker_ids:
                continue
            detections.append(item)
        return detections

    def _filter_recent_memory(self, zone_cfg):
        allowed_groups = set(zone_cfg.get("groups", []))
        allowed_marker_ids = set(zone_cfg.get("allowed_marker_ids", []))
        now_ns = self.get_clock().now().nanoseconds
        window_ns = int(self.memory_window_sec * 1e9)
        detections = []
        expired = []
        for marker_id, (seen_ns, item) in self.detection_memory.items():
            if now_ns - seen_ns > window_ns:
                expired.append(marker_id)
                continue
            group = item.get("group")
            if allowed_groups and group not in allowed_groups:
                continue
            if allowed_marker_ids and marker_id not in allowed_marker_ids:
                continue
            detections.append(item)
        for marker_id in expired:
            self.detection_memory.pop(marker_id, None)
        return detections

    def _build_summary(self, detections):
        summary = {}
        sources = {}
        for item in detections:
            group = item.get("group", "unknown")
            zh_name = item.get("zh_name", "未知目标")
            summary.setdefault(group, {})
            summary[group][zh_name] = summary[group].get(zh_name, 0) + 1
            source = item.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        return summary, sources

    def _source_priority(self, item):
        priority = {
            "yolo": 4,
            "aruco": 3,
            "color": 2,
            "zone_fallback": 1,
        }
        return priority.get(item.get("source", "unknown"), 0)

    def _print_clean_report(self, display_name, summary, sources):
        print(f"\n[{display_name}]")
        if not summary:
            print("识别结果: 未检测到目标", flush=True)
            return
        for group, items in summary.items():
            parts = [f"{name}: {count}" for name, count in sorted(items.items())]
            print(f"{group}: " + "，".join(parts))
        if sources:
            parts = [f"{name}: {count}" for name, count in sorted(sources.items())]
            print("识别来源: " + "，".join(parts), flush=True)

    def _fallback_detections(self, zone_cfg):
        detections = []
        fallback_ids = zone_cfg.get("fallback_marker_ids", [])
        for marker_id in fallback_ids:
            marker_cfg = self._marker_config(marker_id)
            if not marker_cfg:
                continue
            item = {
                "marker_id": int(marker_id),
                "group": marker_cfg.get("group", "unknown"),
                "label": marker_cfg.get("label", "unknown"),
                "zh_name": marker_cfg.get("zh_name", f"marker_{marker_id}"),
                "source": "zone_fallback",
            }
            detections.append(item)
        return detections

    def _marker_config(self, marker_id):
        marker_catalog = {
            1: {"group": "trash_bin", "label": "kitchen", "zh_name": "厨余垃圾桶"},
            2: {"group": "trash_bin", "label": "recyclable", "zh_name": "可回收物垃圾桶"},
            3: {"group": "trash_bin", "label": "hazardous", "zh_name": "有害垃圾桶"},
            4: {"group": "trash_bin", "label": "other", "zh_name": "其他垃圾桶"},
            5: {"group": "people", "label": "medical_rescue", "zh_name": "医疗救助人群"},
            6: {"group": "people", "label": "normal_rescue", "zh_name": "普通救助人群"},
            7: {"group": "people", "label": "normal_rescue", "zh_name": "普通救助人群"},
            8: {"group": "building", "label": "collapse", "zh_name": "坍塌楼宇"},
            9: {"group": "building", "label": "fire", "zh_name": "火灾楼宇"},
            10: {"group": "building", "label": "toxic_gas", "zh_name": "有毒气体楼宇"},
            11: {"group": "building", "label": "power_failure", "zh_name": "电力故障楼宇"},
            12: {"group": "people", "label": "medical_rescue", "zh_name": "医疗救助人群"},
            13: {"group": "people", "label": "normal_rescue", "zh_name": "普通救助人群"},
        }
        return marker_catalog.get(int(marker_id), {})

    def _publish_report(self, payload):
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self.report_pub.publish(msg)


def main():
    rclpy.init()
    node = ResultReporterNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
