import itertools

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ZoneTriggerDemoNode(Node):
    def __init__(self):
        super().__init__("zone_trigger_demo_node")
        self.declare_parameter("trigger_topic", "/safe_city/task/zone_trigger")
        self.declare_parameter("publish_rate_sec", 4.0)
        self.declare_parameter(
            "zones", ["trash_zone", "people_zone", "building_zone"]
        )

        self.trigger_topic = self.get_parameter("trigger_topic").value
        period = float(self.get_parameter("publish_rate_sec").value)
        zones = list(self.get_parameter("zones").value)
        self.publisher = self.create_publisher(String, self.trigger_topic, 10)
        self.zone_cycle = itertools.cycle(zones)
        self.timer = self.create_timer(period, self._publish_next)

        self.get_logger().info("Zone trigger demo ready.")
        self.get_logger().info(f"Publishing triggers on: {self.trigger_topic}")

    def _publish_next(self):
        zone = next(self.zone_cycle)
        msg = String()
        msg.data = zone
        self.publisher.publish(msg)
        self.get_logger().info(f"Triggered zone: {zone}")


def main():
    rclpy.init()
    node = ZoneTriggerDemoNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
