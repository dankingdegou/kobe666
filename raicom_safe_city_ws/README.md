# RAICOM Safe City Workspace

This workspace targets the RAICOM 2026 "Safe City" track with the following stack:

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- Nav2
- SLAM Toolbox
- RViz2
- OpenCV / ArUco
- TurtleBot3 Waffle-derived inspection robot

## Workspace Layout

```text
raicom_safe_city_ws/
├── docs/
├── src/
│   ├── safe_city_bringup/
│   ├── safe_city_description/
│   ├── safe_city_gazebo/
│   ├── safe_city_navigation/
│   └── safe_city_perception/
```

## Next Steps

See the full Chinese usage guide:

```text
docs/usage_guide.md
```

Quick start:

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
bash scripts/build_workspace.sh
source scripts/use_safe_city_env.sh
bash scripts/clean_safe_city_runtime.sh
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```
