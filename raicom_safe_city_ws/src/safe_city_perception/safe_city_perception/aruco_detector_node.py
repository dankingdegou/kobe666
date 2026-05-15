import json
import pathlib

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
import yaml


class ArucoDetectorNode(Node):
    def __init__(self):
        super().__init__("aruco_detector_node")
        default_map = (
            pathlib.Path(__file__).resolve().parents[1] / "config" / "aruco_map.yaml"
        )

        self.declare_parameter("aruco_map_file", str(default_map))
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("result_topic", "/safe_city/perception/detections")
        self.declare_parameter("dictionary_id", "DICT_4X4_50")

        self.image_topic = self.get_parameter("image_topic").value
        self.result_topic = self.get_parameter("result_topic").value
        map_file = self.get_parameter("aruco_map_file").get_parameter_value().string_value

        self.aruco_map = self._load_aruco_map(map_file)
        self.dictionary, self.detector_parameters = self._create_detector_config(
            self.get_parameter("dictionary_id").value
        )

        self.frame_count = 0
        self.last_signature = None
        self.result_pub = self.create_publisher(String, self.result_topic, 10)
        self.image_sub = self.create_subscription(
            Image, self.image_topic, self._image_callback, 10
        )

        self.get_logger().info("Aruco detector node ready.")
        self.get_logger().info(f"Subscribed image topic: {self.image_topic}")
        self.get_logger().info(f"Publishing detections on: {self.result_topic}")
        self.get_logger().info(f"Loaded {len(self.aruco_map)} marker definitions.")

    def _load_aruco_map(self, path_str):
        path = pathlib.Path(path_str)
        if not path.exists():
            self.get_logger().warn(f"Aruco map file not found: {path}")
            return {}

        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        markers = data.get("markers", {})
        return {int(key): value for key, value in markers.items()}

    def _create_detector_config(self, dictionary_name):
        dictionary_attr = getattr(cv2.aruco, dictionary_name, None)
        if dictionary_attr is None:
            raise ValueError(f"Unknown ArUco dictionary: {dictionary_name}")

        dictionary = cv2.aruco.getPredefinedDictionary(dictionary_attr)
        if hasattr(cv2.aruco, "DetectorParameters_create"):
            parameters = cv2.aruco.DetectorParameters_create()
        else:
            parameters = cv2.aruco.DetectorParameters()
        return dictionary, parameters

    def _image_callback(self, msg):
        frame = self._image_msg_to_bgr(msg)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(
            gray,
            self.dictionary,
            parameters=self.detector_parameters,
        )

        self.frame_count += 1
        if self.frame_count % 30 == 0:
            self.get_logger().info(f"Processed {self.frame_count} frames.")

        detections = self._color_detections(frame)
        if (ids is None or len(ids) == 0) and not detections:
            return

        if ids is not None:
            seen_ids = {item["marker_id"] for item in detections}
            for marker_id in ids.flatten().tolist():
                marker_id = int(marker_id)
                if marker_id in seen_ids:
                    continue
                detections.append(self._marker_payload(marker_id, "aruco"))

        payload = {
            "source_topic": self.image_topic,
            "count": len(detections),
            "detections": detections,
        }
        msg_out = String()
        msg_out.data = json.dumps(payload, ensure_ascii=False)
        self.result_pub.publish(msg_out)

        signature = json.dumps(detections, ensure_ascii=False, sort_keys=True)
        if signature == self.last_signature:
            return

        self.last_signature = signature
        readable = ", ".join(
            f"{item['zh_name']}({item['marker_id']})" for item in detections
        )
        self.get_logger().info(f"Detected {len(detections)} marker(s): {readable}")

    def _marker_payload(self, marker_id, source):
        info = self.aruco_map.get(marker_id, {})
        return {
            "marker_id": int(marker_id),
            "group": info.get("group", "unknown"),
            "label": info.get("label", "unknown"),
            "zh_name": info.get("zh_name", f"marker_{marker_id}"),
            "source": source,
        }

    def _color_detections(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        specs = [
            (1, [((42, 80, 45), (82, 255, 255))]),  # green kitchen bin
            (2, [((95, 80, 45), (130, 255, 255))]),  # blue recyclable bin
            (3, [((0, 90, 50), (10, 255, 255)), ((170, 90, 50), (180, 255, 255))]),
            (4, [((132, 70, 45), (158, 255, 255))]),  # purple other bin
            (5, [((82, 70, 45), (94, 255, 255))]),  # cyan medical rescue person
            (6, [((22, 80, 70), (38, 255, 255))]),  # yellow normal rescue person
            (7, [((158, 70, 45), (170, 255, 255))]),  # magenta normal rescue person
            (8, [((0, 0, 55), (180, 45, 145))]),  # gray collapse building
            (9, [((11, 90, 55), (21, 255, 255))]),  # orange fire building
            (10, [((38, 60, 45), (82, 210, 170))]),  # green toxic gas building
            (11, [((95, 45, 45), (125, 210, 170))]),  # blue power failure building
        ]
        detections = []
        kernel = np.ones((3, 3), dtype=np.uint8)
        for marker_id, ranges in specs:
            mask = None
            for low, high in ranges:
                part = cv2.inRange(hsv, np.array(low, dtype=np.uint8), np.array(high, dtype=np.uint8))
                mask = part if mask is None else cv2.bitwise_or(mask, part)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            area = max(cv2.contourArea(contour) for contour in contours)
            if area >= 220.0:
                detections.append(self._marker_payload(marker_id, "color"))
        return detections

    def _image_msg_to_bgr(self, msg):
        if msg.encoding not in {"bgr8", "rgb8", "mono8"}:
            raise ValueError(f"Unsupported image encoding: {msg.encoding}")

        channels = 1 if msg.encoding == "mono8" else 3
        row_stride = msg.step
        expected_stride = msg.width * channels
        if row_stride < expected_stride:
            raise ValueError(
                f"Invalid image step {row_stride} for width={msg.width}, channels={channels}"
            )

        raw = np.frombuffer(msg.data, dtype=np.uint8)
        frame = raw.reshape((msg.height, row_stride))
        frame = frame[:, :expected_stride]
        frame = frame.reshape((msg.height, msg.width, channels)).copy()

        if msg.encoding == "rgb8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        elif msg.encoding == "mono8":
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        return frame


def main():
    rclpy.init()
    node = ArucoDetectorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
