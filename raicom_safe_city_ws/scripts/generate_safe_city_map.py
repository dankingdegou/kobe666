#!/usr/bin/env python3
"""Generate the PDF-style rounded-loop safe-city navigation occupancy map."""

from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
MAP_DIR = WORKSPACE / "src" / "safe_city_navigation" / "maps"
PGM_PATH = MAP_DIR / "safe_city_map.pgm"
YAML_PATH = MAP_DIR / "safe_city_map.yaml"

SIZE_M = 4.0
RESOLUTION = 0.05
CELLS = int(SIZE_M / RESOLUTION)
ORIGIN = -SIZE_M / 2.0


OUTER_W = 3.50
OUTER_H = 3.50
OUTER_R = 0.72
INNER_W = 1.90
INNER_H = 1.90
INNER_R = 0.42


def inside_rounded_rect(x: float, y: float, width: float, height: float, radius: float) -> bool:
    """Return whether a point is inside a rounded rectangle centered at origin."""
    hx = width / 2.0
    hy = height / 2.0
    core_x = hx - radius
    core_y = hy - radius
    qx = abs(x) - core_x
    qy = abs(y) - core_y
    outside_x = max(qx, 0.0)
    outside_y = max(qy, 0.0)
    outside_distance = (outside_x * outside_x + outside_y * outside_y) ** 0.5
    inside_distance = min(max(qx, qy), 0.0)
    return outside_distance + inside_distance <= radius


def is_occupied(x: float, y: float) -> bool:
    """Return occupied cells outside the PDF-style 800 mm rounded loop."""
    if abs(x) >= 1.98 or abs(y) >= 1.98:
        return True

    inside_outer = inside_rounded_rect(x, y, OUTER_W, OUTER_H, OUTER_R)
    inside_inner = inside_rounded_rect(x, y, INNER_W, INNER_H, INNER_R)
    return (not inside_outer) or inside_inner


def main() -> None:
    MAP_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[str] = []
    for row in range(CELLS):
        # PGM row 0 is the top of the image, while map y increases upward.
        y = ORIGIN + (CELLS - row - 0.5) * RESOLUTION
        values: list[str] = []
        for col in range(CELLS):
            x = ORIGIN + (col + 0.5) * RESOLUTION
            values.append("0" if is_occupied(x, y) else "254")
        rows.append(" ".join(values))

    PGM_PATH.write_text(
        "P2\n"
        "# RAICOM Safe City PDF-style rounded-loop navigation map\n"
        f"{CELLS} {CELLS}\n"
        "255\n"
        + "\n".join(rows)
        + "\n",
        encoding="ascii",
    )
    YAML_PATH.write_text(
        "image: safe_city_map.pgm\n"
        "mode: trinary\n"
        f"resolution: {RESOLUTION}\n"
        f"origin: [{ORIGIN}, {ORIGIN}, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.196\n",
        encoding="ascii",
    )

    print(f"Wrote {PGM_PATH} ({CELLS}x{CELLS}, {RESOLUTION} m/cell)")
    print(f"Wrote {YAML_PATH}")


if __name__ == "__main__":
    main()
