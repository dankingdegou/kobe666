import json
import pathlib
import sys
import time

YOLO_VENV_SITE_PACKAGES = (
    pathlib.Path(__file__).resolve().parents[4]
    / "tools"
    / "X-AnyLabeling"
    / ".venv-cpu"
    / "lib"
    / "python3.12"
    / "site-packages"
)
if YOLO_VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(YOLO_VENV_SITE_PACKAGES))

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
import yaml


class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__("yolo_detector_node")
        default_config = (
            pathlib.Path(__file__).resolve().parents[1] / "config" / "yolo_classes.yaml"
        )

        self.declare_parameter("yolo_config_file", str(default_config))
        self.declare_parameter("model_path", "")
        self.declare_parameter("image_topic", "/camera")
        self.declare_parameter("result_topic", "/safe_city/perception/detections")
        self.declare_parameter("confidence_threshold", -1.0)
        self.declare_parameter("image_size", 0)
        self.declare_parameter("publish_every_n_frames", 1)

        self.image_topic = self.get_parameter("image_topic").value
        self.result_topic = self.get_parameter("result_topic").value
        self.publish_every_n_frames = max(
            1, int(self.get_parameter("publish_every_n_frames").value)
        )
        config_file = (
            self.get_parameter("yolo_config_file").get_parameter_value().string_value
        )
        self.config = self._load_config(config_file)
        self.class_by_id = self._class_map_by_id(self.config)

        model_path = self.get_parameter("model_path").get_parameter_value().string_value
        if not model_path:
            model_path = self.config.get("yolo", {}).get("model_path", "")
        self.model_path = self._resolve_model_path(model_path) if model_path else None

        configured_conf = float(self.get_parameter("confidence_threshold").value)
        self.confidence_threshold = (
            configured_conf
            if configured_conf >= 0.0
            else float(self.config.get("yolo", {}).get("confidence_threshold", 0.35))
        )
        configured_imgsz = int(self.get_parameter("image_size").value)
        self.image_size = (
            configured_imgsz
            if configured_imgsz > 0
            else int(self.config.get("yolo", {}).get("image_size", 640))
        )

        self.frame_count = 0
        self.last_signature = None
        self.model = self._load_model()
        self.result_pub = self.create_publisher(String, self.result_topic, 10)

        if self.model is None:
            self.get_logger().warn(
                "YOLO detector is idle. Train a model and set model_path to enable it."
            )
            return

        self.image_sub = self.create_subscription(
            Image, self.image_topic, self._image_callback, 10
        )
        self.get_logger().info("YOLO detector node ready.")
        self.get_logger().info(f"Subscribed image topic: {self.image_topic}")
        self.get_logger().info(f"Publishing detections on: {self.result_topic}")
        self.get_logger().info(f"Loaded YOLO model: {self.model_path}")

    def _load_config(self, path_str):
        path = pathlib.Path(path_str)
        if not path.exists():
            self.get_logger().warn(f"YOLO config file not found: {path}")
            return {}
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _resolve_model_path(self, model_path):
        path = pathlib.Path(model_path).expanduser()
        if path.is_absolute():
            return path
        workspace_model = self._workspace_root() / model_path
        if workspace_model.exists():
            return workspace_model
        config_model = pathlib.Path(__file__).resolve().parents[1] / "config" / model_path
        if config_model.exists():
            return config_model
        return pathlib.Path.cwd() / model_path

    def _workspace_root(self):
        current_file = pathlib.Path(__file__).resolve()
        for parent in current_file.parents:
            if (parent / "models").is_dir() and (parent / "src").is_dir():
                return parent
        for parent in current_file.parents:
            candidate = parent / "raicom_safe_city_ws"
            if (candidate / "models").is_dir() and (candidate / "src").is_dir():
                return candidate
        return current_file.parents[3]

    def _class_map_by_id(self, config):
        class_by_id = {}
        for class_name, item in (config.get("classes", {}) or {}).items():
            mapped = dict(item)
            mapped["class_name"] = class_name
            class_by_id[int(item["id"])] = mapped
        return class_by_id

    def _load_model(self):
        if self.model_path is None or not self.model_path.exists():
            self.get_logger().warn(f"YOLO model file not found: {self.model_path}")
            return None
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            self.get_logger().warn(
                "ultralytics is not installed in this Python environment: "
                f"{exc}. Install it for YOLO inference."
            )
            return None
        try:
            return YOLO(str(self.model_path))
        except Exception as exc:
            self.get_logger().error(f"Failed to load YOLO model: {exc}")
            return None

    def _image_callback(self, msg):
        self.frame_count += 1
        if self.frame_count % self.publish_every_n_frames != 0:
            return

        frame = self._image_msg_to_bgr(msg)
        try:
            results = self.model.predict(
                source=frame,
                imgsz=self.image_size,
                conf=self.confidence_threshold,
                verbose=False,
            )
        except Exception as exc:
            self.get_logger().warn(f"YOLO inference failed: {exc}")
            return

        detections = self._detections_from_results(results)
        if not detections:
            return

        payload = {
            "source_topic": self.image_topic,
            "source": "yolo",
            "stamp_sec": time.time(),
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
            f"{item['zh_name']}({item['confidence']:.2f})" for item in detections
        )
        self.get_logger().info(f"YOLO detected {len(detections)} target(s): {readable}")

    def _detections_from_results(self, results):
        detections = []
        if not results:
            return detections
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections

        for box in boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            class_cfg = self.class_by_id.get(class_id)
            if class_cfg is None:
                continue
            xyxy = box.xyxy[0].detach().cpu().numpy().astype(float).tolist()
            detections.append(
                {
                    "marker_id": int(class_cfg.get("marker_id", class_id)),
                    "group": class_cfg.get("group", "unknown"),
                    "label": class_cfg.get("label", class_cfg.get("class_name", "unknown")),
                    "zh_name": class_cfg.get("zh_name", class_cfg.get("class_name", "未知目标")),
                    "source": "yolo",
                    "class_id": class_id,
                    "class_name": class_cfg.get("class_name", str(class_id)),
                    "confidence": confidence,
                    "bbox_xyxy": xyxy,
                }
            )
        return detections

    def _image_msg_to_bgr(self, msg):
        if msg.encoding not in {"bgr8", "rgb8", "mono8"}:
            raise ValueError(f"Unsupported image encoding: {msg.encoding}")

        channels = 1 if msg.encoding == "mono8" else 3
        expected_stride = msg.width * channels
        if msg.step < expected_stride:
            raise ValueError(
                f"Invalid image step {msg.step} for width={msg.width}, channels={channels}"
            )
        raw = np.frombuffer(msg.data, dtype=np.uint8)
        frame = raw.reshape((msg.height, msg.step))
        frame = frame[:, :expected_stride]
        frame = frame.reshape((msg.height, msg.width, channels)).copy()

        if msg.encoding == "rgb8":
            # Avoid importing cv2 before the node actually needs image conversion.
            frame = frame[:, :, ::-1]
        elif msg.encoding == "mono8":
            frame = np.repeat(frame, 3, axis=2)
        return frame


def main():
    rclpy.init()
    node = YoloDetectorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
