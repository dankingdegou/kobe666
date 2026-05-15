#!/usr/bin/env python3
"""Clean competition console for the RAICOM Safe City demo.

This process is intentionally outside ros2 launch output. It subscribes to the
mission report topics and prints only the final recognition blocks.
"""

import json
import signal
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


EXPECTED_ZONES = ("people_zone", "trash_zone", "building_zone")
GROUP_ORDER = ("people", "trash_bin", "building")
DISPLAY_ORDER = (
    "普通救助人群",
    "医疗救助人群",
    "厨余垃圾桶",
    "可回收物垃圾桶",
    "有害垃圾桶",
    "其他垃圾桶",
    "坍塌楼宇",
    "火灾楼宇",
    "有毒气体楼宇",
    "电力故障楼宇",
)
ALLOWED_NAMES = set(DISPLAY_ORDER)


class CompetitionConsole(Node):
    def __init__(self):
        super().__init__("safe_city_competition_console")
        self.received_zones = set()
        self.completed = False
        self.done = False

        self.create_subscription(
            String,
            "/safe_city/task/zone_report",
            self._report_callback,
            10,
        )
        self.create_subscription(
            String,
            "/safe_city/task/patrol_state",
            self._state_callback,
            10,
        )

        print("RAICOM 平安城市识别结果", flush=True)
        print("等待小车到达识别点...\n", flush=True)

    def _report_callback(self, msg):
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        zone_name = payload.get("zone_name", "")
        display_name = payload.get("display_name") or zone_name or "未知区域"
        summary = payload.get("summary") or {}
        sources = payload.get("sources") or {}
        summary = self._filter_summary(summary)

        if zone_name:
            self.received_zones.add(zone_name)

        print(f"[{display_name}]")
        if not summary:
            print("识别结果: 未检测到目标", flush=True)
            return

        for group, items in self._ordered_groups(summary):
            parts = [f"{name}: {count}" for name, count in self._ordered_items(items)]
            print(f"{group}: " + "，".join(parts))

        if sources:
            parts = [f"{name}: {count}" for name, count in sorted(sources.items())]
            print("识别来源: " + "，".join(parts))

        print("", flush=True)
        self._maybe_finish()

    def _state_callback(self, msg):
        if msg.data.strip() == "completed:full_map_loop":
            self.completed = True
            print("[完成] 小车已完成 PDF 地图闭环巡检并返回起点附近", flush=True)
            self._maybe_finish()

    def _maybe_finish(self):
        if self.completed and all(zone in self.received_zones for zone in EXPECTED_ZONES):
            self.done = True

    def _filter_summary(self, summary):
        filtered = {}
        for group, items in summary.items():
            allowed_items = {
                name: count
                for name, count in items.items()
                if name in ALLOWED_NAMES and int(count) > 0
            }
            if allowed_items:
                filtered[group] = allowed_items
        return filtered

    def _ordered_groups(self, summary):
        for group in GROUP_ORDER:
            if group in summary:
                yield group, summary[group]
        for group in sorted(set(summary) - set(GROUP_ORDER)):
            yield group, summary[group]

    def _ordered_items(self, items):
        order = {name: index for index, name in enumerate(DISPLAY_ORDER)}
        return sorted(items.items(), key=lambda item: (order.get(item[0], len(order)), item[0]))


def main():
    rclpy.init()
    node = CompetitionConsole()

    def handle_signal(_signum, _frame):
        node.done = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
