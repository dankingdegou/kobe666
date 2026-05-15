#!/usr/bin/env python3
"""Generate the PDF-style rounded-loop Safe City Gazebo world."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import cv2
import numpy as np


WORKSPACE = Path(__file__).resolve().parents[1]
WORLD_PATH = WORKSPACE / "src" / "safe_city_gazebo" / "worlds" / "safe_city.world.sdf"
TB3_WAFFLE_XACRO = Path("/opt/ros/jazzy/share/nav2_minimal_tb3_sim/urdf/gz_waffle.sdf.xacro")

FIELD_SIZE = 4.0
OUTER_W = 3.50
OUTER_H = 3.50
OUTER_R = 0.72
INNER_W = 1.90
INNER_H = 1.90
INNER_R = 0.42
TRACK_WIDTH = 0.80
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def _model_from_sdf(sdf_text: str) -> str:
    start = sdf_text.index('<model name="turtlebot3_waffle">')
    end = sdf_text.index("</model>", start) + len("</model>")
    return sdf_text[start:end]


def _insert_into_link(model: str, link_name: str, xml: str) -> str:
    link_start = model.index(f'<link name="{link_name}">')
    link_end = model.index("</link>", link_start)
    return model[:link_end] + xml + model[link_end:]


def _build_tb3_inspection_robot() -> str | None:
    if not TB3_WAFFLE_XACRO.exists():
        return None

    try:
        result = subprocess.run(
            ["xacro", str(TB3_WAFFLE_XACRO), "namespace:="],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    model = _model_from_sdf(result.stdout)
    model = model.replace('<model name="turtlebot3_waffle">', '<model name="inspection_robot">', 1)
    model = model.replace(
        "<pose>0.0 0.0 0.0 0.0 0.0 0.0</pose>",
        "<pose>-1.35 -1.35 0.01 0 0 0</pose>",
        1,
    )
    model = model.replace("<max_linear_velocity>0.46</max_linear_velocity>", "<max_linear_velocity>0.22</max_linear_velocity>")
    model = model.replace("<min_linear_velocity>-0.46</min_linear_velocity>", "<min_linear_velocity>-0.10</min_linear_velocity>")
    model = model.replace("<max_angular_velocity>1.9</max_angular_velocity>", "<max_angular_velocity>0.95</max_angular_velocity>")
    model = model.replace("<min_angular_velocity>-1.9</min_angular_velocity>", "<min_angular_velocity>-0.95</min_angular_velocity>")

    patrol_shell = """
        <visual name="safe_city_patrol_shell">
          <pose>-0.064 0 0.108 0 0 0</pose>
          <geometry><box><size>0.24 0.22 0.045</size></box></geometry>
          <material>
            <ambient>0.06 0.23 0.36 1</ambient>
            <diffuse>0.06 0.23 0.36 1</diffuse>
          </material>
        </visual>
        <visual name="safe_city_status_light">
          <pose>0.045 0 0.16 0 0 0</pose>
          <geometry><cylinder><radius>0.028</radius><length>0.025</length></cylinder></geometry>
          <material>
            <ambient>0.05 0.85 0.95 1</ambient>
            <diffuse>0.05 0.85 0.95 1</diffuse>
            <emissive>0.02 0.35 0.42 1</emissive>
          </material>
        </visual>
"""
    model = _insert_into_link(model, "base_link", patrol_shell)

    rgb_camera = """
        <visual name="safe_city_rgb_camera_body">
          <pose>0.095 0 0.135 0 0 0</pose>
          <geometry><box><size>0.045 0.080 0.035</size></box></geometry>
          <material>
            <ambient>0.01 0.01 0.012 1</ambient>
            <diffuse>0.01 0.01 0.012 1</diffuse>
          </material>
        </visual>
        <sensor name="safe_city_rgb_camera" type="camera">
          <always_on>true</always_on>
          <visualize>true</visualize>
          <update_rate>15</update_rate>
          <pose>0.095 0 0.135 0 0 0</pose>
          <topic>camera</topic>
          <gz_frame_id>camera_link</gz_frame_id>
          <camera name="safe_city_rgb_camera">
            <horizontal_fov>1.047</horizontal_fov>
            <image>
              <width>640</width>
              <height>480</height>
              <format>R8G8B8</format>
            </image>
            <clip>
              <near>0.02</near>
              <far>6.0</far>
            </clip>
          </camera>
        </sensor>
"""
    model = _insert_into_link(model, "camera_link", rgb_camera)
    return "\n".join(f"    {line}" if line else line for line in model.splitlines())


def extract_robot_model() -> str:
    tb3_model = _build_tb3_inspection_robot()
    if tb3_model is not None:
        return tb3_model

    text = WORLD_PATH.read_text(encoding="utf-8")
    start = text.index('    <model name="inspection_robot">')
    end = text.index("  </world>", start)
    robot = text[start:end].rstrip()
    robot = robot.replace(
        "<pose>-1.55 -1.55 0.08 0 0 0</pose>",
        "<pose>-1.35 -1.35 0.08 0 0 0</pose>",
    )
    return robot


def rounded_rect_points(width: float, height: float, radius: float, samples: int = 16):
    hx = width / 2.0
    hy = height / 2.0
    points: list[tuple[float, float]] = []

    # Clockwise, starting near the lower-left straight.
    corners = [
        (-hx + radius, -hy + radius, math.pi, 1.5 * math.pi),
        (hx - radius, -hy + radius, 1.5 * math.pi, 2.0 * math.pi),
        (hx - radius, hy - radius, 0.0, 0.5 * math.pi),
        (-hx + radius, hy - radius, 0.5 * math.pi, math.pi),
    ]
    for cx, cy, a0, a1 in corners:
        for index in range(samples + 1):
            angle = a0 + (a1 - a0) * index / samples
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def box_model(name: str, pose: str, size: str, color: str, collision: bool = True) -> str:
    collision_xml = ""
    if collision:
        collision_xml = f"""
        <collision name="collision">
          <geometry><box><size>{size}</size></box></geometry>
        </collision>"""
    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">{collision_xml}
        <visual name="visual">
          <geometry><box><size>{size}</size></box></geometry>
          <material><ambient>{color}</ambient><diffuse>{color}</diffuse></material>
        </visual>
      </link>
    </model>"""


def segment_box(name: str, p0, p1, width: float, height: float, color: str, collision: bool):
    x0, y0 = p0
    x1, y1 = p1
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length < 0.01:
        return ""
    x = (x0 + x1) / 2.0
    y = (y0 + y1) / 2.0
    yaw = math.atan2(dy, dx)
    return box_model(
        name=name,
        pose=f"{x:.4f} {y:.4f} {height / 2.0:.4f} 0 0 {yaw:.5f}",
        size=f"{length:.4f} {width:.4f} {height:.4f}",
        color=color,
        collision=collision,
    )


def polyline_models(prefix: str, points, width: float, height: float, color: str, collision: bool):
    models = []
    for index, p0 in enumerate(points):
        p1 = points[(index + 1) % len(points)]
        models.append(segment_box(f"{prefix}_{index:02d}", p0, p1, width, height, color, collision))
    return "\n".join(models)


def textured_board(name: str, pose: str, size: str, texture: str) -> str:
    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{size}</size></box></geometry>
          <material>
            <ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse>
            <pbr><metal><albedo_map>../materials/textures/{texture}</albedo_map></metal></pbr>
          </material>
        </visual>
      </link>
    </model>"""


def textured_plane(name: str, pose: str, size: str, texture: str) -> str:
    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">
        <visual name="visual">
          <geometry><plane><size>{size}</size></plane></geometry>
          <material>
            <ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse>
            <pbr><metal><albedo_map>../materials/textures/{texture}</albedo_map></metal></pbr>
          </material>
        </visual>
      </link>
    </model>"""


def marker_cells(marker_id: int, grid: int = 6) -> list[list[int]]:
    size = 600
    marker = np.zeros((size, size), dtype=np.uint8)
    if hasattr(cv2.aruco, "generateImageMarker"):
        cv2.aruco.generateImageMarker(ARUCO_DICT, marker_id, size, marker, 1)
    else:
        cv2.aruco.drawMarker(ARUCO_DICT, marker_id, size, marker, 1)
    cell = size // grid
    cells = []
    for row in range(grid):
        values = []
        for col in range(grid):
            patch = marker[row * cell : (row + 1) * cell, col * cell : (col + 1) * cell]
            values.append(1 if int(patch.mean()) < 128 else 0)
        cells.append(values)
    return cells


def aruco_geometry_marker(
    name: str,
    marker_id: int,
    center_x: float,
    center_y: float,
    center_z: float,
    face: str,
    size: float = 0.24,
) -> str:
    cell_size = size / 6.0
    black = "0.0 0.0 0.0 1"
    white = "1.0 1.0 1.0 1"
    backing_depth = 0.006
    tile_depth = 0.012
    tile_offset = 0.028
    models = []

    if face in ("pos_y", "neg_y"):
        y = center_y + (backing_depth / 2.0 if face == "pos_y" else -backing_depth / 2.0)
        models.append(
            box_model(
                f"{name}_white_backing",
                f"{center_x:.4f} {y:.4f} {center_z:.4f} 0 0 0",
                f"{size:.4f} {backing_depth:.4f} {size:.4f}",
                white,
                False,
            )
        )
        tile_y = center_y + (tile_offset if face == "pos_y" else -tile_offset)
        for row, values in enumerate(marker_cells(marker_id)):
            for col, is_black in enumerate(values):
                if not is_black:
                    continue
                x = center_x - size / 2.0 + (col + 0.5) * cell_size
                z = center_z + size / 2.0 - (row + 0.5) * cell_size
                models.append(
                    box_model(
                        f"{name}_cell_{row}_{col}",
                        f"{x:.4f} {tile_y:.4f} {z:.4f} 0 0 0",
                        f"{cell_size:.4f} {tile_depth:.4f} {cell_size:.4f}",
                        black,
                        False,
                    )
                )
    elif face in ("pos_x", "neg_x"):
        x = center_x + (backing_depth / 2.0 if face == "pos_x" else -backing_depth / 2.0)
        models.append(
            box_model(
                f"{name}_white_backing",
                f"{x:.4f} {center_y:.4f} {center_z:.4f} 0 0 0",
                f"{backing_depth:.4f} {size:.4f} {size:.4f}",
                white,
                False,
            )
        )
        tile_x = center_x + (tile_offset if face == "pos_x" else -tile_offset)
        for row, values in enumerate(marker_cells(marker_id)):
            for col, is_black in enumerate(values):
                if not is_black:
                    continue
                y = center_y - size / 2.0 + (col + 0.5) * cell_size
                z = center_z + size / 2.0 - (row + 0.5) * cell_size
                models.append(
                    box_model(
                        f"{name}_cell_{row}_{col}",
                        f"{tile_x:.4f} {y:.4f} {z:.4f} 0 0 0",
                        f"{tile_depth:.4f} {cell_size:.4f} {cell_size:.4f}",
                        black,
                        False,
                    )
                )
    else:
        raise ValueError(f"Unsupported marker face: {face}")

    return "\n".join(models)


def aruco_geometry_board(prefix: str, marker_ids, base_x: float, base_y: float, z: float, face: str) -> str:
    offsets = [-0.27, -0.09, 0.09, 0.27] if len(marker_ids) == 4 else [-0.22, 0.0, 0.22]
    markers = []
    for marker_id, offset in zip(marker_ids, offsets):
        if face in ("pos_y", "neg_y"):
            x, y = base_x + offset, base_y
        else:
            x, y = base_x, base_y + offset
        markers.append(aruco_geometry_marker(f"{prefix}_{marker_id}", marker_id, x, y, z, face))
    return "\n".join(markers)


def crosswalk_models() -> str:
    bars = []
    for group, y in [("upper", 0.52), ("lower", -0.52)]:
        for index in range(6):
            x = 1.52 + index * 0.08
            bars.append(
                box_model(
                    f"right_crosswalk_{group}_{index}",
                    f"{x:.3f} {y:.3f} 0.032 0 0 0",
                    "0.045 0.34 0.014",
                    "0.96 0.96 0.90 1",
                    collision=False,
                )
            )
    return "\n".join(bars)


def task_models() -> str:
    return f"""
    {box_model("trash_label_plate", "0 1.02 0.05 0 0 0", "0.58 0.26 0.035", "0.92 0.92 0.88 1", False)}
    <model name="trash_bin_models">
      <static>true</static>
      <pose>0 1.10 0.16 0 0 0</pose>
      <link name="link">
        <visual name="kitchen"><pose>-0.27 0 0 0 0 0</pose><geometry><box><size>0.16 0.16 0.32</size></box></geometry><material><ambient>0.05 0.65 0.15 1</ambient><diffuse>0.05 0.65 0.15 1</diffuse></material></visual>
        <visual name="recyclable"><pose>-0.09 0 0 0 0 0</pose><geometry><box><size>0.16 0.16 0.32</size></box></geometry><material><ambient>0.05 0.25 0.85 1</ambient><diffuse>0.05 0.25 0.85 1</diffuse></material></visual>
        <visual name="hazardous"><pose>0.09 0 0 0 0 0</pose><geometry><box><size>0.16 0.16 0.32</size></box></geometry><material><ambient>0.75 0.05 0.05 1</ambient><diffuse>0.75 0.05 0.05 1</diffuse></material></visual>
        <visual name="other"><pose>0.27 0 0 0 0 0</pose><geometry><box><size>0.16 0.16 0.32</size></box></geometry><material><ambient>0.62 0.12 0.85 1</ambient><diffuse>0.62 0.12 0.85 1</diffuse></material></visual>
      </link>
    </model>

    {box_model("people_label_plate", "-1.03 0 0.05 0 0 1.5708", "0.58 0.26 0.035", "0.92 0.92 0.88 1", False)}
    <model name="people_models">
      <static>true</static>
      <pose>-1.08 0 0.3 0 0 0</pose>
      <link name="link">
        <visual name="adult"><pose>0 0.22 0 0 0 0</pose><geometry><cylinder><radius>0.075</radius><length>0.60</length></cylinder></geometry><material><ambient>0.00 0.78 0.82 1</ambient><diffuse>0.00 0.78 0.82 1</diffuse></material></visual>
        <visual name="old_person"><pose>0 0 0 0 0 0</pose><geometry><cylinder><radius>0.075</radius><length>0.55</length></cylinder></geometry><material><ambient>0.95 0.78 0.10 1</ambient><diffuse>0.95 0.78 0.10 1</diffuse></material></visual>
        <visual name="child"><pose>0 -0.22 -0.08 0 0 0</pose><geometry><cylinder><radius>0.065</radius><length>0.42</length></cylinder></geometry><material><ambient>0.95 0.08 0.78 1</ambient><diffuse>0.95 0.08 0.78 1</diffuse></material></visual>
      </link>
    </model>

    {box_model("building_label_plate", "0 -1.02 0.05 0 0 0", "0.58 0.26 0.035", "0.92 0.92 0.88 1", False)}
    <model name="building_models">
      <static>true</static>
      <pose>0 -1.08 0.35 0 0 0</pose>
      <link name="link">
        <visual name="building_a"><pose>-0.23 0 0 0 0 0</pose><geometry><box><size>0.24 0.22 0.70</size></box></geometry><material><ambient>0.55 0.55 0.58 1</ambient><diffuse>0.55 0.55 0.58 1</diffuse></material></visual>
        <visual name="building_b"><pose>0.20 0 0.08 0 0 0</pose><geometry><box><size>0.30 0.22 0.86</size></box></geometry><material><ambient>0.78 0.36 0.16 1</ambient><diffuse>0.78 0.36 0.16 1</diffuse></material></visual>
        <visual name="fire_sign"><pose>0.20 -0.12 0.18 0 0 0</pose><geometry><box><size>0.18 0.035 0.20</size></box></geometry><material><ambient>1.0 0.38 0.0 1</ambient><diffuse>1.0 0.38 0.0 1</diffuse></material></visual>
      </link>
    </model>

    {aruco_geometry_board("trash_marker", [1, 2, 3, 4], 0.0, 1.17, 0.38, "pos_y")}
    {aruco_geometry_board("people_marker", [5, 6, 7], -1.17, 0.0, 0.38, "neg_x")}
    {aruco_geometry_board("building_marker", [8, 9, 10, 11], 0.0, -1.17, 0.38, "neg_y")}
    """


def main() -> None:
    robot_model = extract_robot_model()
    outer_points = rounded_rect_points(OUTER_W, OUTER_H, OUTER_R, samples=14)
    inner_points = rounded_rect_points(INNER_W, INNER_H, INNER_R, samples=14)
    center_points = rounded_rect_points((OUTER_W + INNER_W) / 2.0, (OUTER_H + INNER_H) / 2.0, (OUTER_R + INNER_R) / 2.0, samples=18)

    world = f"""<?xml version="1.0"?>
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

    {box_model("ground_plane_4m", "0 0 0.005 0 0 0", "4 4 0.01", "0.74 0.75 0.72 1", True)}
    {polyline_models("road_surface", center_points, TRACK_WIDTH, 0.012, "0.15 0.16 0.16 1", False)}
    {polyline_models("outer_black_line", outer_points, 0.045, 0.035, "0.02 0.02 0.02 1", True)}
    {polyline_models("inner_black_line", inner_points, 0.045, 0.035, "0.02 0.02 0.02 1", True)}
    {box_model("left_800mm_dimension_line", "-1.36 0 0.035 0 0 0", "0.80 0.012 0.012", "0.86 0.86 0.86 1", False)}
    {crosswalk_models()}
    {task_models()}

{robot_model}
  </world>
</sdf>
"""
    WORLD_PATH.write_text(world, encoding="utf-8")
    print(f"Wrote {WORLD_PATH}")


if __name__ == "__main__":
    main()
