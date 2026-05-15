#!/usr/bin/env python3
import os
from pathlib import Path

import cv2
import numpy as np


BOARD_DIR = Path(__file__).resolve().parents[1] / "src" / "safe_city_gazebo" / "materials" / "textures"
DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


BOARDS = {
    "trash_zone_board.png": {
        "title": "TRASH BIN ZONE",
        "items": [
            (1, "kitchen"),
            (2, "recyclable"),
            (3, "hazardous"),
            (4, "other"),
        ],
        "accent": (210, 235, 255),
    },
    "people_zone_board.png": {
        "title": "PEOPLE ZONE",
        "items": [
            (5, "adult"),
            (6, "old"),
            (7, "child"),
        ],
        "accent": (220, 255, 225),
    },
    "building_zone_board.png": {
        "title": "BUILDING ZONE",
        "items": [
            (8, "collapse"),
            (9, "fire"),
            (10, "gas"),
            (11, "power"),
        ],
        "accent": (255, 232, 215),
    },
}


def make_marker(marker_id: int, size: int) -> np.ndarray:
    marker = np.zeros((size, size), dtype=np.uint8)
    cv2.aruco.drawMarker(DICT, marker_id, size, marker, 1)
    return cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)


def render_board(title: str, items, accent) -> np.ndarray:
    width, height = 1000, 700
    marker_size = 250
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)

    cv2.rectangle(canvas, (0, 0), (width, 80), accent, -1)
    cv2.putText(
        canvas,
        title,
        (35, 54),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (30, 30, 30),
        3,
        cv2.LINE_AA,
    )

    if len(items) <= 3:
        positions = [(95, 170), (375, 170), (655, 170)]
    else:
        positions = [(170, 105), (580, 105), (170, 385), (580, 385)]

    for idx, (marker_id, label) in enumerate(items):
        x, y = positions[idx]
        marker_img = make_marker(marker_id, marker_size)
        canvas[y : y + marker_size, x : x + marker_size] = marker_img
        cv2.rectangle(canvas, (x, y), (x + marker_size, y + marker_size), (20, 20, 20), 2)
        cv2.putText(
            canvas,
            f"ID {marker_id}",
            (x, y + marker_size + 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (20, 20, 20),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            label.upper(),
            (x, y + marker_size + 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (60, 60, 60),
            2,
            cv2.LINE_AA,
        )

    cv2.rectangle(canvas, (20, 20), (width - 20, height - 20), (40, 40, 40), 4)
    return canvas


def main():
    BOARD_DIR.mkdir(parents=True, exist_ok=True)
    for filename, spec in BOARDS.items():
        image = render_board(spec["title"], spec["items"], spec["accent"])
        output = BOARD_DIR / filename
        cv2.imwrite(str(output), image)
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
