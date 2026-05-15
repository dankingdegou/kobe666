#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path

import yaml


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "safe_city_perception"
    / "config"
    / "yolo_classes.yaml"
)
DEFAULT_GAZEBO_DATASET = Path(__file__).resolve().parents[1] / "datasets" / "safe_city_gazebo_yolo"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "datasets" / "safe_city_formal_yolo"

GAZEBO_CLASS_REMAP = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Build the formal 10-class YOLO dataset.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--gazebo-dataset", default=str(DEFAULT_GAZEBO_DATASET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def load_config(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def class_names(config):
    pairs = []
    for name, item in (config.get("classes", {}) or {}).items():
        pairs.append((int(item["id"]), name))
    return {class_id: name for class_id, name in sorted(pairs)}


def reset_output(output):
    if output.exists():
        shutil.rmtree(output)
    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)


def copy_remapped_gazebo(gazebo_root, output):
    count = 0
    for split in ("train", "val"):
        image_dir = gazebo_root / "images" / split
        label_dir = gazebo_root / "labels" / split
        if not image_dir.exists():
            continue
        for image_path in sorted(image_dir.glob("*")):
            label_path = label_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                continue
            remapped = []
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                old_class = int(parts[0])
                if old_class not in GAZEBO_CLASS_REMAP:
                    continue
                parts[0] = str(GAZEBO_CLASS_REMAP[old_class])
                remapped.append(" ".join(parts))
            if not remapped:
                continue
            target_stem = f"gazebo_{image_path.stem}"
            shutil.copy2(image_path, output / "images" / split / f"{target_stem}{image_path.suffix.lower()}")
            (output / "labels" / split / f"{target_stem}.txt").write_text(
                "\n".join(remapped) + "\n",
                encoding="utf-8",
            )
            count += 1
    return count


def source_path(source, config_path):
    path = Path(source).expanduser()
    if path.is_absolute():
        return path
    return (Path(config_path).resolve().parent / path).resolve()


def copy_source_full_boxes(config, config_path, output):
    classes = config.get("classes", {}) or {}
    source_images = config.get("source_images", {}) or {}
    count = 0
    for index, (source, class_name) in enumerate(source_images.items()):
        image_path = source_path(source, config_path)
        if not image_path.exists() or class_name not in classes:
            continue
        class_id = int(classes[class_name]["id"])
        split = "val" if index % 5 == 0 else "train"
        target_stem = f"source_{class_name}_{image_path.stem}"
        shutil.copy2(image_path, output / "images" / split / f"{target_stem}{image_path.suffix.lower()}")
        (output / "labels" / split / f"{target_stem}.txt").write_text(
            f"{class_id} 0.5 0.5 1.0 1.0\n",
            encoding="utf-8",
        )
        count += 1
    return count


def write_data_yaml(output, names):
    payload = {
        "path": str(output),
        "train": "images/train",
        "val": "images/val",
        "names": names,
    }
    with (output / "data.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def main():
    args = parse_args()
    config = load_config(args.config)
    output = Path(args.output).expanduser()
    gazebo_root = Path(args.gazebo_dataset).expanduser()
    reset_output(output)
    gazebo_count = copy_remapped_gazebo(gazebo_root, output)
    source_count = copy_source_full_boxes(config, args.config, output)
    write_data_yaml(output, class_names(config))
    print(f"Formal YOLO dataset: {output}")
    print(f"Gazebo images: {gazebo_count}")
    print(f"Source images: {source_count}")
    print(f"Data file: {output / 'data.yaml'}")


if __name__ == "__main__":
    main()
