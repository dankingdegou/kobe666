import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MockDetectionPublisherNode(Node):
    def __init__(self):
        super().__init__("mock_detection_publisher_node")
        self.declare_parameter("result_topic", "/safe_city/perception/detections")
        self.declare_parameter("publish_rate_hz", 1.0)

        self.result_topic = self.get_parameter("result_topic").value
        self.publisher = self.create_publisher(String, self.result_topic, 10)
        period = 1.0 / max(float(self.get_parameter("publish_rate_hz").value), 0.1)
        self.timer = self.create_timer(period, self._publish_detection)

        self.payload = {
            "source_topic": "/camera/image_raw",
            "count": 10,
            "detections": [
                {"marker_id": 1, "group": "trash_bin", "label": "kitchen", "zh_name": "厨余垃圾桶", "center_px": {"x": 100.0, "y": 100.0}},
                {"marker_id": 2, "group": "trash_bin", "label": "recyclable", "zh_name": "可回收物垃圾桶", "center_px": {"x": 220.0, "y": 100.0}},
                {"marker_id": 3, "group": "trash_bin", "label": "hazardous", "zh_name": "有害垃圾桶", "center_px": {"x": 340.0, "y": 100.0}},
                {"marker_id": 5, "group": "people", "label": "medical_rescue", "zh_name": "医疗救助人群", "center_px": {"x": 480.0, "y": 100.0}},
                {"marker_id": 6, "group": "people", "label": "normal_rescue", "zh_name": "普通救助人群", "center_px": {"x": 600.0, "y": 100.0}},
                {"marker_id": 7, "group": "people", "label": "normal_rescue", "zh_name": "普通救助人群", "center_px": {"x": 720.0, "y": 100.0}},
                {"marker_id": 8, "group": "building", "label": "collapse", "zh_name": "坍塌楼宇", "center_px": {"x": 860.0, "y": 100.0}},
                {"marker_id": 9, "group": "building", "label": "fire", "zh_name": "火灾楼宇", "center_px": {"x": 980.0, "y": 100.0}},
                {"marker_id": 10, "group": "building", "label": "toxic_gas", "zh_name": "有毒气体楼宇", "center_px": {"x": 1100.0, "y": 100.0}},
                {"marker_id": 11, "group": "building", "label": "power_failure", "zh_name": "电力故障楼宇", "center_px": {"x": 1220.0, "y": 100.0}},
            ],
        }

        self.get_logger().info("Mock detection publisher ready.")
        self.get_logger().info(f"Publishing mock detections on: {self.result_topic}")

    def _publish_detection(self):
        msg = String()
        msg.data = json.dumps(self.payload, ensure_ascii=False)
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = MockDetectionPublisherNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
