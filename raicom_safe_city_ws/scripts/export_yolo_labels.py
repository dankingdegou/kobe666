#!/usr/bin/env python3
import argparse
from pathlib import Path

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
        description="Export Safe City class names for annotation tools."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    pairs = []
    for name, item in (config.get("classes", {}) or {}).items():
        pairs.append((int(item["id"]), name, item.get("zh_name", name)))
    pairs.sort()

    names = [name for _, name, _ in pairs]
    (output_dir / "classes.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    (output_dir / "labels.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    (output_dir / "classes_zh.txt").write_text(
        "\n".join(f"{index}: {name} - {zh_name}" for index, name, zh_name in pairs)
        + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(names)} class names to {output_dir}")


if __name__ == "__main__":
    main()
