#!/usr/bin/env python3
import argparse
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import yaml


FORMAL_CLASSES = {
    0: "kitchen_bin",
    1: "recyclable_bin",
    2: "hazardous_bin",
    3: "other_bin",
    4: "collapse_building",
    5: "fire_building",
    6: "toxic_gas_building",
    7: "power_failure_building",
    8: "medical_rescue_person",
    9: "normal_rescue_person",
}


CLASS_SPECS = [
    (0, [((42, 80, 45), (82, 255, 255))]),
    (1, [((95, 80, 45), (130, 255, 255))]),
    (2, [((0, 90, 50), (10, 255, 255)), ((170, 90, 50), (180, 255, 255))]),
    (3, [((132, 70, 45), (158, 255, 255))]),
    (4, [((0, 0, 55), (180, 45, 145))]),
    (5, [((11, 90, 55), (21, 255, 255))]),
    (6, [((38, 60, 45), (82, 210, 170))]),
    (7, [((95, 45, 45), (125, 210, 170))]),
    (8, [((82, 70, 45), (94, 255, 255))]),
    (9, [((22, 80, 70), (38, 255, 255)), ((158, 70, 45), (170, 255, 255))]),
]


class GazeboYoloDatasetCapture(Node):
    def __init__(self, args):
        super().__init__("gazebo_yolo_dataset_capture")
        self.args = args
        self.output = Path(args.output).expanduser()
        self.frame_index = 0
        self.saved_count = 0
        self.start_time = time.monotonic()
        self.kernel = np.ones((3, 3), dtype=np.uint8)
        self._prepare_dirs()
        self._write_data_yaml()
        self.create_subscription(Image, args.topic, self._image_callback, 10)
        print(f"[YOLO-DATA] capturing from {args.topic} -> {self.output}", flush=True)

    @property
    def done(self):
        if self.saved_count >= self.args.max_images:
            return True
        return (time.monotonic() - self.start_time) >= self.args.max_seconds

    def _prepare_dirs(self):
        for split in ("train", "val"):
            (self.output / "images" / split).mkdir(parents=True, exist_ok=True)
            (self.output / "labels" / split).mkdir(parents=True, exist_ok=True)

    def _write_data_yaml(self):
        names = FORMAL_CLASSES
        payload = {
            "path": str(self.output),
            "train": "images/train",
            "val": "images/val",
            "names": names,
        }
        with (self.output / "data.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)

    def _image_callback(self, msg):
        self.frame_index += 1
        if self.frame_index % self.args.sample_every != 0:
            return
        if self.done:
            return

        frame = self._image_msg_to_bgr(msg)
        labels = self._labels_from_frame(frame)
        if not labels:
            return

        split = "val" if self.saved_count % self.args.val_every == 0 else "train"
        stem = f"gazebo_{self.saved_count:05d}"
        image_path = self.output / "images" / split / f"{stem}.jpg"
        label_path = self.output / "labels" / split / f"{stem}.txt"
        cv2.imwrite(str(image_path), frame)
        label_path.write_text("\n".join(labels) + "\n", encoding="utf-8")

        self.saved_count += 1
        if self.saved_count % 10 == 0:
            print(f"[YOLO-DATA] saved {self.saved_count} images", flush=True)

    def _labels_from_frame(self, frame):
        height, width = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        labels = []
        for class_id, ranges in CLASS_SPECS:
            mask = None
            for low, high in ranges:
                part = cv2.inRange(hsv, np.array(low, dtype=np.uint8), np.array(high, dtype=np.uint8))
                mask = part if mask is None else cv2.bitwise_or(mask, part)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, self.kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.args.min_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                if w < 4 or h < 4:
                    continue
                pad = self.args.pad_pixels
                x1 = max(0, x - pad)
                y1 = max(0, y - pad)
                x2 = min(width - 1, x + w + pad)
                y2 = min(height - 1, y + h + pad)
                cx = ((x1 + x2) / 2.0) / width
                cy = ((y1 + y2) / 2.0) / height
                bw = (x2 - x1) / width
                bh = (y2 - y1) / height
                labels.append(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        return labels

    def _image_msg_to_bgr(self, msg):
        if msg.encoding not in {"bgr8", "rgb8", "mono8"}:
            raise ValueError(f"Unsupported image encoding: {msg.encoding}")
        channels = 1 if msg.encoding == "mono8" else 3
        expected_stride = msg.width * channels
        raw = np.frombuffer(msg.data, dtype=np.uint8)
        frame = raw.reshape((msg.height, msg.step))[:, :expected_stride]
        frame = frame.reshape((msg.height, msg.width, channels)).copy()
        if msg.encoding == "rgb8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        elif msg.encoding == "mono8":
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        return frame


def parse_args():
    parser = argparse.ArgumentParser(description="Capture auto-labeled YOLO images from the Gazebo camera.")
    default_output = Path(__file__).resolve().parents[1] / "datasets" / "safe_city_gazebo_yolo"
    parser.add_argument("--output", default=str(default_output))
    parser.add_argument("--topic", default="/camera")
    parser.add_argument("--max-images", type=int, default=240)
    parser.add_argument("--max-seconds", type=float, default=150.0)
    parser.add_argument("--sample-every", type=int, default=5)
    parser.add_argument("--val-every", type=int, default=5)
    parser.add_argument("--min-area", type=float, default=160.0)
    parser.add_argument("--pad-pixels", type=int, default=8)
    return parser.parse_args()


def main():
    args = parse_args()
    rclpy.init()
    node = GazeboYoloDatasetCapture(args)
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        print(f"[YOLO-DATA] finished with {node.saved_count} images", flush=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
