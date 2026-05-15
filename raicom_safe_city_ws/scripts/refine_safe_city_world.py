#!/usr/bin/env python3
"""Generate the Gazebo world from the RAICOM Safe City PDF map.

The PDF field is a 4000 mm x 4000 mm square with an 800 mm wide rounded
rectangular patrol lane. The robot model is preserved from the existing world;
this script regenerates only the field, markings, targets, and matching map.
"""

from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "src/safe_city_gazebo/worlds/safe_city.world.sdf"
MAP = ROOT / "src/safe_city_navigation/maps/safe_city_map.pgm"

BLACK = (0.02, 0.02, 0.02)
FIELD = (0.84, 0.84, 0.80)
ROAD = (0.70, 0.71, 0.67)
TARGET_GREEN = (0.12, 0.33, 0.20)
TARGET_BLUE = (0.15, 0.28, 0.42)
TARGET_BROWN = (0.36, 0.25, 0.16)


def material(r: float, g: float, b: float, a: float = 1.0) -> str:
    return (
        f"<material><ambient>{r:.3f} {g:.3f} {b:.3f} {a:.1f}</ambient>"
        f"<diffuse>{r:.3f} {g:.3f} {b:.3f} {a:.1f}</diffuse></material>"
    )


def box_model(
    name: str,
    pose: str,
    size: str,
    color: tuple[float, float, float],
    *,
    collision: bool = False,
) -> str:
    collision_xml = ""
    if collision:
        collision_xml = (
            "        <collision name=\"collision\">\n"
            f"          <geometry><box><size>{size}</size></box></geometry>\n"
            "        </collision>\n"
        )
    return f"""    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">
{collision_xml}        <visual name="visual">
          <geometry><box><size>{size}</size></box></geometry>
          {material(*color)}
        </visual>
      </link>
    </model>
"""


def cylinder_model(
    name: str,
    pose: str,
    radius: float,
    length: float,
    color: tuple[float, float, float],
) -> str:
    return f"""    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">
        <visual name="visual">
          <geometry><cylinder><radius>{radius:.3f}</radius><length>{length:.3f}</length></cylinder></geometry>
          {material(*color)}
        </visual>
      </link>
    </model>
"""


def line_segment(
    name: str,
    x: float,
    y: float,
    length: float,
    yaw: float,
    *,
    width: float = 0.045,
    height: float = 0.008,
    color: tuple[float, float, float] = BLACK,
) -> str:
    return box_model(
        name,
        f"{x:.4f} {y:.4f} 0.018 0 0 {yaw:.5f}",
        f"{length:.4f} {width:.4f} {height:.4f}",
        color,
    )


def rounded_rect_line(
    prefix: str,
    half_x: float,
    half_y: float,
    radius: float,
    *,
    width: float = 0.050,
    arc_steps: int = 18,
) -> list[str]:
    parts: list[str] = []
    straight_x = 2.0 * (half_x - radius)
    straight_y = 2.0 * (half_y - radius)

    parts.append(line_segment(f"{prefix}_top", 0.0, half_y, straight_x, 0.0, width=width))
    parts.append(line_segment(f"{prefix}_bottom", 0.0, -half_y, straight_x, 0.0, width=width))
    parts.append(line_segment(f"{prefix}_left", -half_x, 0.0, straight_y, math.pi / 2.0, width=width))
    parts.append(line_segment(f"{prefix}_right", half_x, 0.0, straight_y, math.pi / 2.0, width=width))

    corners = [
        (half_x - radius, half_y - radius, 0.0, math.pi / 2.0),
        (-(half_x - radius), half_y - radius, math.pi / 2.0, math.pi),
        (-(half_x - radius), -(half_y - radius), math.pi, 3.0 * math.pi / 2.0),
        (half_x - radius, -(half_y - radius), 3.0 * math.pi / 2.0, 2.0 * math.pi),
    ]
    arc_len = radius * ((math.pi / 2.0) / arc_steps) * 1.25
    for ci, (cx, cy, start, end) in enumerate(corners):
        for i in range(arc_steps):
            theta = start + (i + 0.5) * (end - start) / arc_steps
            x = cx + radius * math.cos(theta)
            y = cy + radius * math.sin(theta)
            yaw = theta + math.pi / 2.0
            parts.append(line_segment(f"{prefix}_arc_{ci:02d}_{i:02d}", x, y, arc_len, yaw, width=width))
    return parts


def cylinder_visual(name: str, pose: str, radius: float, length: float, color: tuple[float, float, float]) -> str:
    return f"""        <visual name="{name}">
          <pose>{pose}</pose>
          <geometry><cylinder><radius>{radius:.3f}</radius><length>{length:.3f}</length></cylinder></geometry>
          {material(*color)}
        </visual>
"""


def scene_layer() -> str:
    parts: list[str] = []
    parts.append(box_model("ground_plane_4m", "0 0 0.000 0 0 0", "4.00 4.00 0.004", FIELD, collision=True))

    # Thin square boundary: the PDF shows a 4000 mm x 4000 mm square around the rounded lane.
    parts.append(line_segment("field_border_north", 0.0, 2.0, 4.0, 0.0, width=0.025, height=0.004))
    parts.append(line_segment("field_border_south", 0.0, -2.0, 4.0, 0.0, width=0.025, height=0.004))
    parts.append(line_segment("field_border_east", 2.0, 0.0, 4.0, math.pi / 2.0, width=0.025, height=0.004))
    parts.append(line_segment("field_border_west", -2.0, 0.0, 4.0, math.pi / 2.0, width=0.025, height=0.004))

    # The road itself is the 800 mm band between outer and inner rounded rectangles.
    parts.append(box_model("road_top_band", "0 1.35 0.006 0 0 0", "2.10 0.80 0.006", ROAD))
    parts.append(box_model("road_bottom_band", "0 -1.35 0.006 0 0 0", "2.10 0.80 0.006", ROAD))
    parts.append(box_model("road_left_band", "-1.35 0 0.006 0 0 0", "0.80 2.10 0.006", ROAD))
    parts.append(box_model("road_right_band", "1.35 0 0.006 0 0 0", "0.80 2.10 0.006", ROAD))
    for name, x, y in [
        ("road_corner_ne", 1.05, 1.05),
        ("road_corner_nw", -1.05, 1.05),
        ("road_corner_sw", -1.05, -1.05),
        ("road_corner_se", 1.05, -1.05),
    ]:
        parts.append(cylinder_model(name, f"{x:.2f} {y:.2f} 0.006 0 0 0", 0.82, 0.006, ROAD))

    parts.extend(rounded_rect_line("outer_track_line", 1.75, 1.75, 0.70, width=0.055))
    parts.extend(rounded_rect_line("inner_track_line", 0.95, 0.95, 0.42, width=0.055))

    # 800 mm dimension marker on the left, exactly where the PDF annotates lane width.
    parts.append(line_segment("dimension_800mm_line", -1.35, 0.30, 0.80, 0.0, width=0.010, height=0.003, color=(0.45, 0.45, 0.45)))
    parts.append(box_model("dimension_800mm_tick_outer", "-1.75 0.30 0.016 0 0 0", "0.010 0.12 0.003", (0.45, 0.45, 0.45)))
    parts.append(box_model("dimension_800mm_tick_inner", "-0.95 0.30 0.016 0 0 0", "0.010 0.12 0.003", (0.45, 0.45, 0.45)))

    # PDF right-side zebra crossings: two black-stripe groups, printed flat on the lane.
    for group, y in [("upper", 0.55), ("lower", -0.55)]:
        for i, x in enumerate([1.08, 1.20, 1.32, 1.44, 1.56, 1.68]):
            parts.append(box_model(f"right_zebra_{group}_{i}", f"{x:.2f} {y:.2f} 0.022 0 0 0", "0.055 0.28 0.004", BLACK))
    parts.append(line_segment("right_zebra_separator_upper", 1.38, 0.35, 0.70, 0.0, width=0.025, height=0.004))
    parts.append(line_segment("right_zebra_separator_lower", 1.38, -0.35, 0.70, 0.0, width=0.025, height=0.004))

    # Target zones follow the PDF: trash on inner top, people on inner left, buildings on inner bottom.
    parts.append(box_model("trash_zone_plate", "0 0.72 0.020 0 0 0", "0.75 0.26 0.006", TARGET_GREEN))
    parts.append(box_model("people_zone_plate", "-0.72 0 0.020 0 0 1.5708", "0.75 0.26 0.006", TARGET_BLUE))
    parts.append(box_model("building_zone_plate", "0 -0.72 0.020 0 0 0", "0.75 0.26 0.006", TARGET_BROWN))

    parts.append("""    <model name="trash_bin_models">
      <static>true</static>
      <pose>0 0.80 0.16 0 0 0</pose>
      <link name="link">
        <visual name="kitchen"><pose>-0.30 0 0 0 0 0</pose><geometry><box><size>0.15 0.15 0.32</size></box></geometry><material><ambient>0.05 0.65 0.15 1</ambient><diffuse>0.05 0.65 0.15 1</diffuse></material></visual>
        <visual name="recyclable"><pose>-0.10 0 0 0 0 0</pose><geometry><box><size>0.15 0.15 0.32</size></box></geometry><material><ambient>0.05 0.25 0.85 1</ambient><diffuse>0.05 0.25 0.85 1</diffuse></material></visual>
        <visual name="hazardous"><pose>0.10 0 0 0 0 0</pose><geometry><box><size>0.15 0.15 0.32</size></box></geometry><material><ambient>0.75 0.05 0.05 1</ambient><diffuse>0.75 0.05 0.05 1</diffuse></material></visual>
        <visual name="other"><pose>0.30 0 0 0 0 0</pose><geometry><box><size>0.15 0.15 0.32</size></box></geometry><material><ambient>0.62 0.12 0.85 1</ambient><diffuse>0.62 0.12 0.85 1</diffuse></material></visual>
      </link>
    </model>
""")

    parts.append("""    <model name="people_models">
      <static>true</static>
      <pose>-0.80 0 0.30 0 0 0</pose>
      <link name="link">
""")
    parts.append(cylinder_visual("adult", "0 0.24 0 0 0 0", 0.070, 0.60, (0.00, 0.78, 0.82)))
    parts.append(cylinder_visual("old_person", "0 0 0 0 0 0", 0.070, 0.55, (0.95, 0.78, 0.10)))
    parts.append(cylinder_visual("child", "0 -0.24 -0.08 0 0 0", 0.062, 0.42, (0.95, 0.08, 0.78)))
    parts.append("""      </link>
    </model>
""")

    parts.append("""    <model name="building_models">
      <static>true</static>
      <pose>0 -0.80 0.35 0 0 0</pose>
      <link name="link">
        <visual name="collapse_building"><pose>-0.32 0 -0.05 0 0 0</pose><geometry><box><size>0.24 0.22 0.58</size></box></geometry><material><ambient>0.42 0.42 0.43 1</ambient><diffuse>0.42 0.42 0.43 1</diffuse></material></visual>
        <visual name="fire_building"><pose>-0.10 0 0.08 0 0 0</pose><geometry><box><size>0.22 0.22 0.86</size></box></geometry><material><ambient>0.72 0.30 0.12 1</ambient><diffuse>0.72 0.30 0.12 1</diffuse></material></visual>
        <visual name="toxic_gas_building"><pose>0.12 0 0.03 0 0 0</pose><geometry><box><size>0.22 0.22 0.76</size></box></geometry><material><ambient>0.20 0.55 0.25 1</ambient><diffuse>0.20 0.55 0.25 1</diffuse></material></visual>
        <visual name="power_failure_building"><pose>0.34 0 0.00 0 0 0</pose><geometry><box><size>0.22 0.22 0.70</size></box></geometry><material><ambient>0.20 0.22 0.55 1</ambient><diffuse>0.20 0.22 0.55 1</diffuse></material></visual>
        <visual name="fire_sign"><pose>-0.10 -0.12 0.20 0 0 0</pose><geometry><box><size>0.16 0.030 0.18</size></box></geometry><material><ambient>1.0 0.38 0.0 1</ambient><diffuse>1.0 0.38 0.0 1</diffuse><emissive>0.55 0.18 0.0 1</emissive></material></visual>
      </link>
    </model>
""")

    includes = [
        ("trash_marker_1_board", "-0.3000 0.9650 0.0300 0 0 0"),
        ("trash_marker_2_board", "-0.1000 0.9650 0.0300 0 0 0"),
        ("trash_marker_3_board", "0.1000 0.9650 0.0300 0 0 0"),
        ("trash_marker_4_board", "0.3000 0.9650 0.0300 0 0 0"),
        ("people_marker_5_board", "-0.9650 -0.2400 0.0300 0 0 1.5708"),
        ("people_marker_6_board", "-0.9650 0.0000 0.0300 0 0 1.5708"),
        ("people_marker_7_board", "-0.9650 0.2400 0.0300 0 0 1.5708"),
        ("building_marker_8_board", "-0.3000 -0.9650 0.0300 0 0 0"),
        ("building_marker_9_board", "-0.1000 -0.9650 0.0300 0 0 0"),
        ("building_marker_10_board", "0.1000 -0.9650 0.0300 0 0 0"),
        ("building_marker_11_board", "0.3000 -0.9650 0.0300 0 0 0"),
    ]
    for model, pose in includes:
        parts.append(f"    <include><uri>model://{model}</uri><name>{model}</name><pose>{pose}</pose></include>\n")

    return "\n".join(parts)


def write_navigation_map() -> None:
    """Write an 80x80 occupancy map aligned with the 4m square field."""

    width = height = 80
    resolution = 0.05
    origin = -2.0
    data = [[254 for _ in range(width)] for _ in range(height)]

    def world_to_px(x: float, y: float) -> tuple[int, int]:
        px = int(round((x - origin) / resolution))
        py = int(round((2.0 - y) / resolution))
        return px, py

    def set_disk(cx: float, cy: float, radius: float, value: int = 0) -> None:
        pcx, pcy = world_to_px(cx, cy)
        pr = max(1, int(math.ceil(radius / resolution)))
        for yy in range(max(0, pcy - pr), min(height, pcy + pr + 1)):
            for xx in range(max(0, pcx - pr), min(width, pcx + pr + 1)):
                if (xx - pcx) ** 2 + (yy - pcy) ** 2 <= pr * pr:
                    data[yy][xx] = value

    def set_segment(x1: float, y1: float, x2: float, y2: float, thickness: float, value: int = 0) -> None:
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / (resolution * 0.5)))
        for i in range(steps + 1):
            t = i / steps
            set_disk(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, thickness, value)

    # Field edge and rounded lane boundaries. This gives Nav2 the same map shape
    # as the Gazebo visual world without making the road itself artificially blocked.
    for x1, y1, x2, y2 in [(-2, 2, 2, 2), (-2, -2, 2, -2), (-2, -2, -2, 2), (2, -2, 2, 2)]:
        set_segment(x1, y1, x2, y2, 0.03)

    for half_x, half_y, radius in [(1.75, 1.75, 0.70), (0.95, 0.95, 0.42)]:
        set_segment(-(half_x - radius), half_y, half_x - radius, half_y, 0.035)
        set_segment(-(half_x - radius), -half_y, half_x - radius, -half_y, 0.035)
        set_segment(-half_x, -(half_y - radius), -half_x, half_y - radius, 0.035)
        set_segment(half_x, -(half_y - radius), half_x, half_y - radius, 0.035)
        for cx, cy, start, end in [
            (half_x - radius, half_y - radius, 0, math.pi / 2),
            (-(half_x - radius), half_y - radius, math.pi / 2, math.pi),
            (-(half_x - radius), -(half_y - radius), math.pi, 3 * math.pi / 2),
            (half_x - radius, -(half_y - radius), 3 * math.pi / 2, 2 * math.pi),
        ]:
            steps = 32
            prev = None
            for i in range(steps + 1):
                theta = start + (end - start) * i / steps
                point = (cx + radius * math.cos(theta), cy + radius * math.sin(theta))
                if prev is not None:
                    set_segment(prev[0], prev[1], point[0], point[1], 0.035)
                prev = point

    MAP.write_text(
        "P2\n"
        "# RAICOM Safe City PDF rounded-rectangle map\n"
        f"{width} {height}\n"
        "255\n"
        + "\n".join(" ".join(str(v) for v in row) for row in data)
        + "\n",
        encoding="ascii",
    )


def main() -> None:
    text = WORLD.read_text(encoding="utf-8")
    marker = '    <model name="inspection_robot">'
    start = text.find(marker)
    if start == -1:
        raise RuntimeError("inspection_robot model not found; refusing to rewrite world")
    robot_and_tail = text[start:]
    prefix = """<?xml version="1.0"?>
<sdf version="1.9">
  <world name="safe_city">
    <gravity>0 0 -9.8</gravity>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.85 0.85 0.85 1</diffuse>
      <specular>0.25 0.25 0.25 1</specular>
      <direction>-0.4 0.2 -0.9</direction>
    </light>

"""
    WORLD.write_text(prefix + scene_layer() + "\n" + robot_and_tail, encoding="utf-8")
    write_navigation_map()


if __name__ == "__main__":
    main()
