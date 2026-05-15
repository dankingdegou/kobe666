#!/usr/bin/env python3
"""Build a YOLO dataset that matches the photo-billboard Gazebo targets."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
import yaml


WS = Path(__file__).resolve().parents[1]
TEXTURE_DIR = WS / "src" / "safe_city_gazebo" / "materials" / "textures"
DEFAULT_OUTPUT = WS / "datasets" / "safe_city_billboard_yolo"

CLASSES = {
    0: ("kitchen_bin", "kitchen_bin.jpg"),
    1: ("recyclable_bin", "recyclable_bin.jpg"),
    2: ("hazardous_bin", "hazardous_bin.jpg"),
    3: ("other_bin", "other_bin.jpg"),
    4: ("collapse_building", "collapse_building.jpg"),
    5: ("fire_building", "fire_building.jpg"),
    6: ("toxic_gas_building", "toxic_gas_building.jpg"),
    7: ("power_failure_building", "power_failure_building.jpg"),
    8: ("medical_rescue_person", "medical_rescue_person.jpg"),
    9: ("normal_rescue_person", "normal_rescue_person.jpg"),
}

SCENES = {
    "trash": [0, 1, 2, 3],
    "people": [8, 9, 9],
    "building": [4, 5, 6, 7],
}


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic billboard YOLO data.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--train", type=int, default=720)
    parser.add_argument("--val", type=int, default=160)
    parser.add_argument("--seed", type=int, default=2026)
    return parser.parse_args()


def load_textures():
    textures = {}
    for class_id, (_name, filename) in CLASSES.items():
        image = cv2.imread(str(TEXTURE_DIR / filename), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(TEXTURE_DIR / filename)
        textures[class_id] = image
    return textures


def reset_output(output: Path):
    if output.exists():
        for path in sorted(output.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)


def make_background(rng: random.Random, width: int = 640, height: int = 480):
    base = np.zeros((height, width, 3), dtype=np.uint8)
    road = rng.randint(112, 150)
    base[:] = (road, road + rng.randint(-4, 8), road + rng.randint(-8, 6))
    cv2.rectangle(base, (0, 0), (width, int(height * 0.32)), (170, 176, 166), -1)
    cv2.rectangle(base, (0, int(height * 0.72)), (width, height), (92, 96, 90), -1)
    for _ in range(rng.randint(8, 18)):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        color = rng.randint(80, 185)
        cv2.circle(base, (x, y), rng.randint(1, 3), (color, color, color), -1)
    noise = np.random.default_rng(rng.randint(0, 1_000_000)).normal(0, 5, base.shape)
    return np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def resize_crop(image, target_w: int, target_h: int):
    h, w = image.shape[:2]
    scale = max(target_w / w, target_h / h)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    y0 = max(0, (resized.shape[0] - target_h) // 2)
    x0 = max(0, (resized.shape[1] - target_w) // 2)
    return resized[y0 : y0 + target_h, x0 : x0 + target_w]


def paste_billboard(canvas, texture, x: int, y: int, w: int, h: int, rng: random.Random):
    patch = resize_crop(texture, w, h)
    brightness = rng.uniform(0.78, 1.18)
    patch = np.clip(patch.astype(np.float32) * brightness, 0, 255).astype(np.uint8)
    if rng.random() < 0.25:
        patch = cv2.GaussianBlur(patch, (3, 3), 0)
    canvas[y : y + h, x : x + w] = patch
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (28, 28, 28), 2)


def label_line(class_id, x, y, w, h, width=640, height=480):
    cx = (x + w / 2) / width
    cy = (y + h / 2) / height
    return f"{class_id} {cx:.6f} {cy:.6f} {w / width:.6f} {h / height:.6f}"


def make_scene(textures, rng: random.Random):
    canvas = make_background(rng)
    scene_name = rng.choice(list(SCENES))
    class_ids = SCENES[scene_name][:]
    rng.shuffle(class_ids)
    labels = []

    if scene_name == "trash":
        y = rng.randint(168, 235)
        box_w = rng.randint(82, 112)
        box_h = rng.randint(145, 190)
        gap = rng.randint(8, 18)
        total_w = len(class_ids) * box_w + (len(class_ids) - 1) * gap
        x0 = rng.randint(60, max(61, 640 - total_w - 60))
    elif scene_name == "people":
        y = rng.randint(115, 195)
        box_w = rng.randint(86, 122)
        box_h = rng.randint(190, 265)
        gap = rng.randint(14, 28)
        total_w = len(class_ids) * box_w + (len(class_ids) - 1) * gap
        x0 = rng.randint(70, max(71, 640 - total_w - 70))
    else:
        y = rng.randint(88, 165)
        box_w = rng.randint(92, 128)
        box_h = rng.randint(230, 330)
        gap = rng.randint(8, 18)
        total_w = len(class_ids) * box_w + (len(class_ids) - 1) * gap
        x0 = rng.randint(35, max(36, 640 - total_w - 35))

    for index, class_id in enumerate(class_ids):
        x = x0 + index * (box_w + gap) + rng.randint(-4, 4)
        h = max(48, int(box_h * rng.uniform(0.86, 1.08)))
        w = max(36, int(box_w * rng.uniform(0.88, 1.08)))
        y_i = min(460 - h, max(8, y + rng.randint(-12, 12)))
        paste_billboard(canvas, textures[class_id], x, y_i, w, h, rng)
        labels.append(label_line(class_id, x, y_i, w, h))

    return canvas, labels


def write_data_yaml(output: Path):
    payload = {
        "path": str(output),
        "train": "images/train",
        "val": "images/val",
        "names": {class_id: name for class_id, (name, _filename) in CLASSES.items()},
    }
    with (output / "data.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def main():
    args = parse_args()
    output = Path(args.output).expanduser()
    rng = random.Random(args.seed)
    textures = load_textures()
    reset_output(output)
    write_data_yaml(output)

    for split, count in (("train", args.train), ("val", args.val)):
        for index in range(count):
            image, labels = make_scene(textures, rng)
            stem = f"{split}_{index:05d}"
            cv2.imwrite(str(output / "images" / split / f"{stem}.jpg"), image)
            (output / "labels" / split / f"{stem}.txt").write_text(
                "\n".join(labels) + "\n",
                encoding="utf-8",
            )
    print(f"Billboard YOLO dataset: {output}")
    print(f"Data file: {output / 'data.yaml'}")


if __name__ == "__main__":
    main()
