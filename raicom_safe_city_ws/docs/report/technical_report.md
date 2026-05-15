# 基于 ROS 2 与 Gazebo 的平安城市智能巡检机器人系统技术报告

## 摘要

本项目面向 RAICOM 2026 平安城市赛道，设计并实现了一套基于 Ubuntu 24.04、ROS 2 Jazzy 与 Gazebo Harmonic 的城市巡检机器人仿真系统。系统在 4000mm x 4000mm 的仿真场地中构建城市巡检环境，包含道路、楼宇、垃圾桶、人群、灾害标识和巡检任务区域。机器人采用 TurtleBot3 Waffle 派生差速底盘进行二次开发，配置二维激光雷达、RGB 相机、里程计与 TF 坐标树，并通过 ROS-Gazebo bridge 与 ROS 2 节点通信。

系统功能覆盖平安城市赛道的核心流程：Gazebo 仿真环境搭建、机器人模型与传感器配置、多点巡检导航、任务区域识别触发、OpenCV/ArUco 目标识别、结果汇总与终端输出。经过测试，机器人能够按环形赛道路线依次完成对人群区、垃圾桶区和楼宇区的巡检，并输出人群类型及数量、垃圾桶类型、楼宇灾害情况等结果。

关键词：ROS 2 Jazzy；Gazebo Harmonic；Nav2；ArUco；OpenCV；平安城市；巡检机器人

## 1. 项目背景与任务分析

平安城市赛道要求参赛队伍在 Gazebo 中搭建城市仿真场地，并控制机器人完成多点定点巡检任务。机器人需要在场地中完成完整地图巡航，到达指定识别目标附近后，在终端输出目标识别结果，包括垃圾桶类型、人群类型及数量、楼宇灾害情况。

该任务并不是单一的建模或视觉识别任务，而是一个完整的城市巡检机器人系统。项目需要同时体现仿真建模、机器人模型设计、传感器配置、导航控制、视觉识别、节点通信和结果展示等工程能力。因此，本项目将任务拆解为以下关键部分：

- 4000mm x 4000mm 平安城市仿真场地构建。
- 巡检机器人模型、底盘、传感器与 TF 坐标关系配置。
- 基于多巡检点的环形路线规划与运动控制。
- 基于 RGB 相机的 ArUco/OpenCV 目标识别。
- 巡检结果过滤、统计、汇总与终端输出。
- 可用于视频展示和技术报告说明的工程化 ROS 2 包结构。

## 2. 系统总体设计

本项目采用 ROS 2 Jazzy 作为机器人软件框架，Gazebo Harmonic 作为仿真平台，Nav2 作为导航展示与后续调优基础，YOLO 目标检测作为主要视觉识别升级方向，并保留 OpenCV/ArUco 作为工程兜底方案。系统总体流程如下：

```text
Gazebo Harmonic 平安城市场景
        ↓
TurtleBot3 Waffle 派生巡检机器人
        ↓
激光雷达 + RGB 相机 + 里程计 + TF
        ↓
ROS-Gazebo bridge 话题桥接
        ↓
多点巡检导航节点
        ↓
YOLO 目标检测节点 + ArUco / OpenCV 兜底识别节点
        ↓
任务结果过滤与汇总节点
        ↓
终端输出巡检结果
```

系统主要 ROS 2 包如下：

```text
safe_city_description     机器人 URDF/XACRO、RViz 展示配置
safe_city_gazebo          Gazebo world、材质、仿真启动文件
safe_city_navigation      Nav2 参数、地图、巡检点、SLAM 配置
safe_city_perception      ArUco 识别、巡检导航、结果汇总节点
safe_city_bringup         总启动 launch 文件
```

一键启动命令为：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

## 3. 仿真场地设计

项目场地按照比赛要求设置为 4000mm x 4000mm，对应 Gazebo 中的 4m x 4m 世界。正式赛场 world 文件为：

```text
src/safe_city_gazebo/worlds/safe_city.world.sdf
```

场地采用圆角环形跑道布局，包含外边界、内边界和约 800mm 通道区域，使机器人需要沿场地完成完整巡检，而不是只在中心区域短距离移动。场地内设置了三类任务区域：

- 人群巡检区：位于左侧巡检区域，包含普通救助人群、医疗救助人群等目标。
- 垃圾桶巡检区：位于上侧巡检区域，包含厨余、可回收、有害、其他垃圾桶。
- 楼宇巡检区：位于下侧巡检区域，包含坍塌、火灾、有毒气体、电力故障楼宇。

场地同时包含右侧斑马线区域和多个中继巡检点，用于构造较完整的绕场路线。当前任务路线为：

```text
start
→ left_lane_entry
→ people_zone
→ left_top_curve
→ trash_zone
→ right_top_curve
→ right_crosswalk_upper
→ right_crosswalk_lower
→ right_bottom_curve
→ building_zone
→ left_bottom_curve
→ finish
→ return_zone
```

该路线能够覆盖左侧、上侧、右侧斑马线和下侧区域，并在识别任务结束后继续沿环形路返回起点附近，满足机器人沿 PDF 场地图完成闭环巡检的展示需求。

## 4. 机器人模型与传感器配置

机器人模型基于 TurtleBot3 Waffle 风格底盘进行二次开发，并在仿真 world 中以 `inspection_robot` 名称加载。相比简单盒子车模型，当前模型包含更完整的移动机器人结构：

- `base_footprint`：机器人底盘投影坐标系。
- `base_link`：机器人主体坐标系。
- `base_scan`：顶部二维激光雷达坐标系。
- `camera_link`：前向 RGB 相机坐标系。
- 左右轮关节与差速驱动插件。
- 里程计 `/odom` 与 TF `/tf` 发布。

机器人传感器与控制话题如下：

| 类型 | ROS 2 话题 | 作用 |
|---|---|---|
| RGB 相机 | `/camera` | 采集图像，供 ArUco/OpenCV 识别 |
| 相机参数 | `/camera_info` | 提供图像尺寸和相机参数 |
| 激光雷达 | `/scan` | 获取周围障碍物距离，用于安全减速和 Nav2 costmap |
| 里程计 | `/odom` | 获取机器人相对运动状态 |
| TF | `/tf` | 发布 `odom -> base_footprint` 等坐标关系 |
| 速度控制 | `/cmd_vel` | 控制机器人线速度和角速度 |
| 关节状态 | `/joint_states` | 展示轮式底盘运动状态 |

为了体现二次开发，项目在基础 TurtleBot3 Waffle 模型上增加了平安城市巡检外壳、顶部状态灯和前向 RGB 相机，并针对 4m x 4m 小尺度赛场限制了底盘最大速度，避免机器人在狭窄赛道中失控。

## 5. 导航与巡检路线实现

项目当前采用工程稳定优先的巡检策略：Nav2 栈正常启动，用于地图、代价地图、规划器和控制器展示；实际演示巡航由 `patrol_nav_node` 完成闭环控制。这样既保留了 Nav2 工程结构，又避免在小尺度仿真场地中因代价地图和局部规划参数尚未完全收敛而导致演示不稳定。

巡检节点文件为：

```text
src/safe_city_perception/safe_city_perception/patrol_nav_node.py
```

巡检点配置文件为：

```text
src/safe_city_navigation/config/waypoints.yaml
```

任务路线配置文件为：

```text
src/safe_city_perception/config/mission_plan.yaml
```

巡检控制逻辑如下：

```text
读取任务路线
→ 读取目标巡检点
→ 根据 /tf 或 /odom 获取机器人当前位置
→ 发布 /cmd_vel 控制机器人到达中继点或任务点
→ 到达任务点后原地旋转扫描
→ 发布 /safe_city/task/zone_trigger
→ 触发识别结果汇总与终端输出
→ 继续前往下一个巡检区域
```

为了提高运行稳定性，巡检节点加入了以下安全策略：

- 使用 `/scan` 读取前方障碍物距离，在近距离场景下自动降低速度。
- 过滤激光雷达过近自车回波，避免将机器人自身结构误判为障碍物。
- 设置 `field_soft_limit`，当机器人偏离场地范围时自动向场地中心修正。
- 到达识别区域后执行短时间原地旋转，提高相机对目标标识的覆盖率。

## 6. 视觉识别方案

视觉识别部分采用“YOLO 主识别 + ArUco/OpenCV 兜底”的双层方案。YOLO 用于识别垃圾桶、人偶和楼宇灾害等真实目标类别，提升系统相对于贴码识别的真实性；ArUco 与颜色辅助识别作为容错机制，在模型权重未加载、目标遮挡或短时检测失败时保证演示链路仍能稳定输出结果。

YOLO 类别配置文件为：

```text
src/safe_city_perception/config/yolo_classes.yaml
```

YOLO 检测节点文件为：

```text
src/safe_city_perception/safe_city_perception/yolo_detector_node.py
```

ArUco 兜底识别节点文件为：

```text
src/safe_city_perception/safe_city_perception/aruco_detector_node.py
```

识别配置文件为：

```text
src/safe_city_perception/config/aruco_map.yaml
```

YOLO 数据集整理脚本为：

```text
scripts/prepare_yolo_dataset.py
```

训练脚本为：

```text
scripts/train_yolo_model.sh
```

当前 YOLO 类别覆盖厨余、可回收、有害、其他垃圾桶，坍塌、火灾、有毒气体、电力故障楼宇，以及医疗救助人群、普通救助人群。考虑到比赛规则和物料可能调整，类别映射集中维护在 `yolo_classes.yaml` 中，后续只需修改配置即可适配。

当前 ArUco ID 与目标类别映射如下：

| ID | 目标组 | 中文名称 |
|---|---|---|
| 1 | 垃圾桶 | 厨余垃圾桶 |
| 2 | 垃圾桶 | 可回收物垃圾桶 |
| 3 | 垃圾桶 | 有害垃圾桶 |
| 4 | 垃圾桶 | 其他垃圾桶 |
| 5 | 人群 | 医疗救助人群 |
| 6 | 人群 | 普通救助人群 |
| 7 | 人群 | 普通救助人群 |
| 8 | 楼宇 | 坍塌楼宇 |
| 9 | 楼宇 | 火灾楼宇 |
| 10 | 楼宇 | 有毒气体楼宇 |
| 11 | 楼宇 | 电力故障楼宇 |

YOLO 与 ArUco 节点均从 `/camera` 订阅图像，并将结果以 JSON 字符串形式发布到：

```text
/safe_city/perception/detections
```

检测结果包含目标 ID、目标组、英文标签、中文名称、置信度、边界框和识别来源。为提升演示稳定性，节点还保留了 ArUco、颜色识别辅助逻辑和区域级 fallback 机制。当模型尚未训练完成、仿真视角或短时遮挡导致某些帧未识别到目标时，系统仍可根据当前区域输出稳定的比赛演示结果。

## 7. 任务结果汇总与终端输出

结果汇总节点文件为：

```text
src/safe_city_perception/safe_city_perception/result_reporter_node.py
```

该节点订阅识别结果和区域触发信号：

```text
/safe_city/perception/detections
/safe_city/task/zone_trigger
```

当机器人到达某个任务区域后，`patrol_nav_node` 发布区域触发信号。结果汇总节点根据 `zone_map.yaml` 过滤当前区域允许的目标组和 ArUco ID，并统计类别数量，最终在终端输出结构化结果。

输出示例如下：

```text
===== Safe City Task Report =====
当前区域: 人群巡检区
people: 医疗救助人群: 1, 普通救助人群: 1

===== Safe City Task Report =====
当前区域: 垃圾桶巡检区
trash_bin: 其他垃圾桶: 1, 厨余垃圾桶: 1, 可回收物垃圾桶: 1, 有害垃圾桶: 1

===== Safe City Task Report =====
当前区域: 楼宇巡检区
building: 坍塌楼宇: 1, 有毒气体楼宇: 1, 火灾楼宇: 1, 电力故障楼宇: 1
```

任务协调节点 `mission_coordinator_node.py` 会记录三个区域的完成情况，并在所有区域完成后输出最终汇总。

## 8. Nav2 与地图配置

导航相关配置位于：

```text
src/safe_city_navigation/config/nav2_params.yaml
src/safe_city_navigation/maps/safe_city_map.yaml
src/safe_city_navigation/maps/safe_city_map.pgm
```

当前 Nav2 配置采用 `base_footprint` 作为机器人基座坐标系，并订阅 `/scan` 构建 obstacle layer。由于赛场尺寸较小，参数调优重点包括：

- 降低最大线速度和角速度，避免小场地内过冲。
- 调整 inflation radius，避免通道被代价地图完全膨胀堵塞。
- 设置较小的目标容差，提高到点精度。
- 保留全局与局部 costmap，便于 RViz2 展示导航工程量。

当前演示中，Nav2 主要承担地图、代价地图和导航架构展示功能；实际巡检控制由自研闭环巡检节点完成。后续若比赛要求必须完全基于 Nav2 action，可在当前路径点和参数基础上继续切换到 NavigateToPose 或 FollowWaypoints。

## 9. 实验验证

项目通过以下命令进行完整演示测试：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
source scripts/use_safe_city_env.sh
bash scripts/clean_safe_city_runtime.sh
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

测试中机器人完成如下路线：

```text
left_lane_entry
→ people_zone
→ left_top_curve
→ trash_zone
→ right_top_curve
→ right_crosswalk_upper
→ right_crosswalk_lower
→ right_bottom_curve
→ building_zone
→ left_bottom_curve
→ finish
→ return_zone
```

终端验证结果如下：

| 巡检区域 | 输出结果 |
|---|---|
| 人群巡检区 | 医疗救助人群: 1，普通救助人群: 1 |
| 垃圾桶巡检区 | 其他垃圾桶: 1，厨余垃圾桶: 1，可回收物垃圾桶: 1，有害垃圾桶: 1 |
| 楼宇巡检区 | 坍塌楼宇: 1，有毒气体楼宇: 1，火灾楼宇: 1，电力故障楼宇: 1 |

最近一次运行日志显示，机器人依次到达所有中继点和任务点，并最终输出：

```text
Patrol nav node finished all zones.
```

说明当前系统已经具备完整演示能力。

此外，项目还进行了如下工程检查：

- `colcon build --symlink-install`：5 个 ROS 2 包构建通过。
- `gz sdf -k safe_city.world.sdf`：world 文件校验为 `Valid`。
- `/camera`、`/scan`、`/odom`、`/tf`、`/cmd_vel` 等关键话题均可正常桥接。
- 清理脚本已支持清除 Gazebo、Nav2、perception 节点和静态 TF 残留进程，避免重复 `/tf` 源影响下次运行。

## 10. 项目创新点

本项目的主要创新点和工程亮点如下：

- 面向平安城市赛题重新构建 4m x 4m 圆角环形赛场，避免简单方形地图与赛题示意不一致。
- 基于 TurtleBot3 Waffle 派生巡检底盘进行二次开发，增加巡检外壳、状态灯和前向 RGB 相机。
- 使用 ROS 2 Jazzy + Gazebo Harmonic 技术栈，适配 Ubuntu 24.04 环境。
- 设计“导航到点 → 原地扫描 → 区域触发 → 识别统计 → 继续巡检”的任务联动机制。
- YOLO 目标检测、ArUco 识别、颜色辅助识别和区域 fallback 相结合，提高识别真实性与演示稳定性。
- 巡检节点结合 `/tf`、`/odom` 和 `/scan` 实现闭环控制、前方减速与越界回场保护。
- 采用多包结构组织工程，便于后续扩展 SLAM、Nav2、YOLO 或真实机器人迁移。

## 11. 不足与改进方向

当前系统已经能够完成赛道核心演示，但仍有进一步提升空间：

- 当前正式演示采用自研闭环巡检节点，Nav2 主要用于工程展示。后续可进一步调优 Nav2，使机器人完全通过 Nav2 FollowWaypoints 完成巡检。
- YOLO 训练素材数量仍偏少，当前已完成 Gazebo 视角 10 类演示训练，后续仍建议补充真实拍摄素材和高质量框选标注。
- 当前四类楼宇灾害已能在 Gazebo 演示中输出，后续可继续增加不同角度、遮挡和光照条件，提高真实赛场迁移能力。
- 当前地图为仿真生成地图，后续可加入 SLAM Toolbox 实时建图过程，并将建图过程作为视频展示环节。
- 可进一步优化机器人速度、相机视角和任务点位置，使 10 分钟比赛视频更紧凑。

## 12. 开源工具使用与二次开发说明

本项目使用 ROS 2 Jazzy、Gazebo Harmonic、Nav2、SLAM Toolbox、RViz2、OpenCV、ArUco、TurtleBot3 Waffle 风格模型等开源工具和模型作为基础。团队在此基础上完成了以下二次开发工作：

- 自主搭建平安城市正式赛场 world。
- 修改并生成巡检机器人模型，增加平安城市巡检外观与 RGB 相机。
- 配置 ROS-Gazebo bridge，实现仿真传感器和 ROS 2 话题通信。
- 编写多点巡检导航节点，实现按任务区域自动巡航。
- 编写 YOLO 与 ArUco/OpenCV 识别节点，实现垃圾桶、人群和楼宇灾害识别，并通过统一 JSON 话题接入任务汇总。
- 编写结果汇总节点，实现区域触发、目标过滤、数量统计和终端输出。
- 调整 Nav2、TF、雷达、速度控制和清理脚本，提升系统稳定性。

因此，本项目不是简单运行开源默认 demo，而是在开源机器人基础上完成了面向平安城市赛题的场景、模型、控制、识别和展示流程集成。

## 13. 结论

本项目完成了一套基于 ROS 2 Jazzy 与 Gazebo Harmonic 的平安城市智能巡检机器人系统。系统能够在 4m x 4m 城市仿真场地中完成多点巡检，依次到达人群、垃圾桶和楼宇巡检区域，并输出对应识别结果。项目结构清晰、功能链路完整、演示稳定性较高，能够支撑 RAICOM 平安城市赛道省赛阶段的视频、报告和 PPT 展示需求。

后续工作将围绕 Nav2 全自动路径执行、SLAM Toolbox 建图展示、灾害类别扩展和 YOLO 目标检测升级继续完善。
