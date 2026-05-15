#!/usr/bin/env python3
import argparse
import random
import shutil
from pathlib import Path
import re

import yaml


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "safe_city_perception"
    / "config"
    / "yolo_classes.yaml"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "datasets" / "safe_city_yolo"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a YOLO dataset scaffold from RAICOM Safe City source images."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--val-ratio", type=float, default=0.25)
    parser.add_argument(
        "--val-all",
        action="store_true",
        help="Copy every image to both train and val for tiny clean baseline datasets.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--bootstrap-full-box",
        action="store_true",
        help=(
            "Create one full-image label per source image. This is only a fast "
            "bootstrap; replace labels with hand-made boxes before serious training."
        ),
    )
    return parser.parse_args()


def load_config(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def class_names_by_id(config):
    pairs = []
    for name, item in (config.get("classes", {}) or {}).items():
        pairs.append((int(item["id"]), name))
    return [name for _, name in sorted(pairs)]


def source_path(source, config_path):
    path = Path(source).expanduser()
    if path.is_absolute():
        return path
    return (Path(config_path).resolve().parent / path).resolve()


def copy_dataset(config, config_path, output, val_ratio, seed, bootstrap_full_box, val_all):
    source_images = config.get("source_images", {}) or {}
    classes = config.get("classes", {}) or {}
    items = []
    for source, class_name in source_images.items():
        path = source_path(source, config_path)
        if not path.exists():
            print(f"[WARN] Missing source image: {path}")
            continue
        if class_name not in classes:
            print(f"[WARN] Unknown class for {path}: {class_name}")
            continue
        items.append((path, class_name, int(classes[class_name]["id"])))

    random.Random(seed).shuffle(items)
    val_count = max(1, int(round(len(items) * val_ratio))) if len(items) > 1 else 0
    val_items = set(path for path, _, _ in items[:val_count])

    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)

    for path, class_name, class_id in items:
        splits = ("train", "val") if val_all else (
            "val" if path in val_items else "train",
        )
        for split in splits:
            safe_stem = safe_name(f"{class_name}_{path.parent.name}_{path.stem}")
            target_image = output / "images" / split / f"{safe_stem}{path.suffix.lower()}"
            target_label = output / "labels" / split / f"{safe_stem}.txt"
            shutil.copy2(path, target_image)

            if bootstrap_full_box:
                target_label.write_text(
                    f"{class_id} 0.5 0.5 1.0 1.0\n", encoding="utf-8"
                )
            elif not target_label.exists():
                target_label.write_text("", encoding="utf-8")

            print(f"[{split}] {path} -> {class_name}")

    names = class_names_by_id(config)
    data_yaml = {
        "path": str(output),
        "train": "images/train",
        "val": "images/val",
        "names": {index: name for index, name in enumerate(names)},
    }
    with (output / "data.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data_yaml, handle, allow_unicode=True, sort_keys=False)
    readme = output / "README.md"
    readme.write_text(
        "# Safe City YOLO Dataset\n\n"
        "This dataset was generated from the repository `平安城市` source images.\n\n"
        "- Empty label files mean the images still need manual YOLO box annotation.\n"
        "- If `--bootstrap-full-box` was used, labels are full-image boxes and should "
        "be treated as a quick baseline only.\n"
        "- Recommended next step: add Gazebo camera screenshots from multiple distances, "
        "angles, and lighting conditions, then relabel or verify all boxes.\n",
        encoding="utf-8",
    )
    return len(items), output / "data.yaml"


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "image"


def main():
    args = parse_args()
    config = load_config(args.config)
    output = Path(args.output).expanduser()
    count, data_yaml = copy_dataset(
        config,
        args.config,
        output,
        args.val_ratio,
        args.seed,
        args.bootstrap_full_box,
        args.val_all,
    )
    print(f"\nCreated dataset with {count} image(s): {output}")
    print(f"YOLO data file: {data_yaml}")


if __name__ == "__main__":
    main()
