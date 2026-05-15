import math

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class TestImagePublisherNode(Node):
    def __init__(self):
        super().__init__("test_image_publisher_node")
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("dictionary_id", "DICT_4X4_50")
        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("image_width", 1280)
        self.declare_parameter("image_height", 720)

        self.image_topic = self.get_parameter("image_topic").value
        self.publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.image_width = int(self.get_parameter("image_width").value)
        self.image_height = int(self.get_parameter("image_height").value)
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, self.image_topic, 10)
        self.detector_dict = self._load_dictionary(
            self.get_parameter("dictionary_id").value
        )
        self.frame_index = 0

        period = 1.0 / max(self.publish_rate_hz, 0.1)
        self.timer = self.create_timer(period, self._publish_image)

        self.get_logger().info("Test image publisher ready.")
        self.get_logger().info(f"Publishing synthetic frames on: {self.image_topic}")

    def _load_dictionary(self, dictionary_name):
        dictionary_attr = getattr(cv2.aruco, dictionary_name, None)
        if dictionary_attr is None:
            raise ValueError(f"Unknown ArUco dictionary: {dictionary_name}")
        return cv2.aruco.getPredefinedDictionary(dictionary_attr)

    def _draw_marker(self, marker_id, size_px):
        marker = np.zeros((size_px, size_px), dtype=np.uint8)
        if hasattr(cv2.aruco, "generateImageMarker"):
            cv2.aruco.generateImageMarker(
                self.detector_dict, marker_id, size_px, marker, 1
            )
        else:
            cv2.aruco.drawMarker(self.detector_dict, marker_id, size_px, marker, 1)
        return cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)

    def _publish_image(self):
        canvas = np.full((self.image_height, self.image_width, 3), 245, dtype=np.uint8)
        self._draw_scene(canvas)

        msg = self.bridge.cv2_to_imgmsg(canvas, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(msg)
        self.frame_index += 1

    def _draw_scene(self, canvas):
        cv2.putText(
            canvas,
            "RAICOM Safe City Perception Test",
            (40, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (30, 30, 30),
            3,
            cv2.LINE_AA,
        )

        sections = [
            ("Trash Bin Zone", (60, 110), [1, 2, 3]),
            ("People Zone", (440, 110), [5, 6, 7]),
            ("Building Zone", (830, 110), [8, 9, 10, 11]),
        ]

        box_width = 320
        box_height = 500
        marker_size = 120
        oscillation = 12 * math.sin(self.frame_index * 0.15)

        for idx, (title, origin, marker_ids) in enumerate(sections):
            x0, y0 = origin
            x1 = x0 + box_width
            y1 = y0 + box_height
            color = [(180, 210, 255), (210, 255, 210), (220, 220, 255)][idx]
            cv2.rectangle(canvas, (x0, y0), (x1, y1), color, -1)
            cv2.rectangle(canvas, (x0, y0), (x1, y1), (70, 70, 70), 2)
            cv2.putText(
                canvas,
                title,
                (x0 + 16, y0 + 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (40, 40, 40),
                2,
                cv2.LINE_AA,
            )

            for marker_index, marker_id in enumerate(marker_ids):
                marker_img = self._draw_marker(marker_id, marker_size)
                marker_x = x0 + 28 + (marker_index % 2) * 150
                marker_y = y0 + 70 + (marker_index // 2) * 170
                marker_y = int(marker_y + oscillation * ((marker_index % 2) * 2 - 1))
                canvas[
                    marker_y : marker_y + marker_size,
                    marker_x : marker_x + marker_size,
                ] = marker_img
                cv2.putText(
                    canvas,
                    f"ID {marker_id}",
                    (marker_x, marker_y + marker_size + 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (20, 20, 20),
                    2,
                    cv2.LINE_AA,
                )


def main():
    rclpy.init()
    node = TestImagePublisherNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
