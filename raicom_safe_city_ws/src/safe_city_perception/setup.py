from setuptools import find_packages, setup

package_name = "safe_city_perception"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/launch",
            [
                "launch/perception.launch.py",
                "launch/perception_test.launch.py",
                "launch/perception_mock_test.launch.py",
                "launch/mission_demo.launch.py",
                "launch/mission_pipeline.launch.py",
                "launch/mission_nav2.launch.py",
            ],
        ),
        (
            "share/" + package_name + "/config",
            [
                "config/aruco_map.yaml",
                "config/zone_map.yaml",
                "config/mission_plan.yaml",
                "config/yolo_classes.yaml",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="RAICOM Team",
    maintainer_email="team@example.com",
    description="Perception nodes for the safe city project.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "aruco_detector_node = safe_city_perception.aruco_detector_node:main",
            "yolo_detector_node = safe_city_perception.yolo_detector_node:main",
            "result_reporter_node = safe_city_perception.result_reporter_node:main",
            "rotate_scan_node = safe_city_perception.rotate_scan_node:main",
            "test_image_publisher_node = safe_city_perception.test_image_publisher_node:main",
            "mock_detection_publisher_node = safe_city_perception.mock_detection_publisher_node:main",
            "zone_trigger_demo_node = safe_city_perception.zone_trigger_demo_node:main",
            "mission_coordinator_node = safe_city_perception.mission_coordinator_node:main",
            "patrol_trigger_node = safe_city_perception.patrol_trigger_node:main",
            "patrol_nav_node = safe_city_perception.patrol_nav_node:main",
        ],
    },
)
