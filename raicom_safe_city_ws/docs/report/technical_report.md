# 基于 ROS 2 与 Gazebo 的平安城市智能巡检机器人系统技术报告

## 摘要

本项目面向 2026 睿抗机器人开发者大赛 RAICOM 全域安防省赛“平安城市”任务，设计并实现了一套基于 ROS 2 Jazzy、Gazebo Harmonic、Nav2 与 YOLO 视觉识别的智能巡检机器人仿真系统。系统以 4000mm x 4000mm 比赛场地为约束，在 Gazebo 中构建圆角环形道路、斑马线、垃圾桶巡检区、人群巡检区和楼宇巡检区，并基于 TurtleBot3 Waffle 风格底盘完成巡检机器人二次开发。机器人搭载二维激光雷达、前向 RGB 相机、里程计与 TF 坐标系统，通过 ROS-Gazebo bridge 将仿真传感器数据接入 ROS 2 节点，实现“场地巡航、定点识别、结果统计、终端展示”的完整任务闭环。

在视觉识别方面，项目采用 YOLO 作为主识别方法，识别结果严格收敛到 10 个比赛类别：普通救助人群、医疗救助人群、厨余垃圾桶、可回收物垃圾桶、有害垃圾桶、其他垃圾桶、坍塌楼宇、火灾楼宇、有毒气体楼宇、电力故障楼宇。同时，为保证比赛演示稳定性，系统保留 ArUco、OpenCV 颜色识别与区域先验作为工程兜底机制。经过完整仿真测试，机器人能够沿 PDF 风格正式赛场完成闭环巡检，并在到达人群、垃圾桶和楼宇巡检点后由 YOLO 输出对应识别结果。

关键词：ROS 2 Jazzy；Gazebo Harmonic；Nav2；YOLO；ArUco；平安城市；巡检机器人；目标检测

## 1. 项目背景与任务分析

平安城市赛题强调机器人在城市环境中的自主巡检与异常识别能力。参赛作品不仅需要搭建符合赛题要求的仿真场地，还需要控制机器人沿规定区域完成巡检，并在到达指定识别点后输出目标类别与数量。该任务综合考察机器人建模、仿真环境构建、运动控制、视觉识别、ROS 2 节点通信和工程集成能力。

结合赛题 PDF 与项目实际实现，本系统将任务拆解为以下几个核心目标：

- 构建 4m x 4m 平安城市正式赛场，包含环形道路、任务区、斑马线和城市目标元素。
- 设计具有差速驱动能力的巡检机器人，配置相机、激光雷达、里程计和 TF 坐标关系。
- 规划覆盖三大任务区的闭环巡检路线，使机器人完成从起点出发、绕场巡检、返回起点附近的完整流程。
- 使用 YOLO 对人群、垃圾桶和楼宇灾害进行图像识别，避免视觉系统只依赖 ArUco 码。
- 在终端中以干净、比赛友好的形式输出识别结果，避免 ROS launch 日志和 Gazebo 日志干扰展示。
- 保留工程兜底机制，在模型缺失、短时遮挡或识别失败时仍能维持演示链路稳定。

因此，本项目不是单独的仿真建模或单独的图像识别任务，而是一套完整的城市巡检机器人系统。

## 2. 系统总体设计

系统采用分层架构设计，从下到上依次为仿真层、机器人层、通信层、导航任务层、视觉感知层和结果展示层。

```text
Gazebo Harmonic 正式赛场
        ↓
巡检机器人模型与传感器
        ↓
ROS-Gazebo bridge 话题桥接
        ↓
Nav2 / 地图 / TF / 巡检控制节点
        ↓
YOLO 主识别 + ArUco/OpenCV 兜底识别
        ↓
区域触发、结果过滤、类别统计
        ↓
干净比赛终端输出
```

项目采用 ROS 2 多包结构组织，主要包如下：

| ROS 2 包 | 主要功能 |
|---|---|
| `safe_city_description` | 机器人 URDF/XACRO、RViz 展示配置 |
| `safe_city_gazebo` | Gazebo world、材质、模型、仿真启动文件 |
| `safe_city_navigation` | Nav2 参数、地图、巡检点、SLAM 配置 |
| `safe_city_perception` | YOLO、ArUco、巡检控制、结果汇总节点 |
| `safe_city_bringup` | 总启动 launch，整合仿真、导航与感知 |

一键演示命令为：

```bash
bash scripts/run_clean_demo.sh
```

该命令默认启动 Gazebo 图形界面，并将 ROS/Gazebo 详细日志写入 `log/competition_demo/`。终端只保留识别结果输出，便于录屏和现场答辩展示。

## 3. 仿真赛场设计

### 3.1 场地尺寸与布局

项目按照比赛要求将场地设置为 4000mm x 4000mm，对应 Gazebo 中 4m x 4m 世界。正式 world 文件位于：

```text
src/safe_city_gazebo/worlds/safe_city.world.sdf
```

场地采用圆角环形道路结构，包含外边界、内边界和约 800mm 通道宽度。相比简单矩形地图，圆角环形道路能更好体现机器人需要沿场地持续巡航，而不是在单个局部区域短距离移动。

场地中设置三类核心任务区域：

| 区域 | 场地位置 | 识别目标 |
|---|---|---|
| 人群巡检区 | 左侧通道附近 | 普通救助人群、医疗救助人群 |
| 垃圾桶巡检区 | 上侧通道附近 | 厨余、可回收物、有害、其他垃圾桶 |
| 楼宇巡检区 | 下侧通道附近 | 坍塌、火灾、有毒气体、电力故障楼宇 |

此外，场地右侧设置斑马线区域，用于增强正式赛场观感和城市道路语义。斑马线采用贴地图案方式放置在平面道路上，而不是做成凸起障碍，避免机器人在巡航过程中被不合理几何结构干扰。

### 3.2 目标与材质设计

为便于 YOLO 识别，项目为各类目标生成了独立视觉纹理，并将其放置在 Gazebo 场景中。目标类别与终端中文输出严格统一，避免出现非比赛口径的历史类别名称。

当前正式输出类别如下：

```text
普通救助人群
医疗救助人群
厨余垃圾桶
可回收物垃圾桶
有害垃圾桶
其他垃圾桶
坍塌楼宇
火灾楼宇
有毒气体楼宇
电力故障楼宇
```

## 4. 机器人模型与传感器配置

项目机器人基于 TurtleBot3 Waffle 风格差速底盘进行二次开发，在 Gazebo 中以 `inspection_robot` 形式加载。模型保留了轮式移动机器人所需的基本结构，并增加平安城市巡检外壳、顶部状态灯与前向 RGB 相机，以体现面向赛题的二次开发。

主要坐标系包括：

| 坐标系 | 含义 |
|---|---|
| `map` | 全局地图坐标系 |
| `odom` | 里程计坐标系 |
| `base_footprint` | 机器人底盘投影坐标系 |
| `base_link` | 机器人主体坐标系 |
| `base_scan` | 顶部二维激光雷达坐标系 |
| `camera_link` | 前向 RGB 相机坐标系 |

机器人关键话题如下：

| 类型 | ROS 2 话题 | 作用 |
|---|---|---|
| RGB 相机 | `/camera` | 采集图像，供 YOLO 与 ArUco/OpenCV 识别 |
| 相机参数 | `/camera_info` | 提供图像尺寸与相机信息 |
| 激光雷达 | `/scan` | 进行前方障碍检测和安全减速 |
| 里程计 | `/odom` | 获取机器人运动状态 |
| TF | `/tf` | 发布机器人坐标变换关系 |
| 速度控制 | `/cmd_vel` | 控制机器人线速度和角速度 |
| 关节状态 | `/joint_states` | 展示差速轮运动状态 |

机器人速度参数针对 4m x 4m 小尺度赛场进行了限制，避免在狭窄通道和转弯区域出现过冲。

## 5. 导航与巡检控制

### 5.1 巡检路线

当前巡检点配置文件为：

```text
src/safe_city_navigation/config/waypoints.yaml
```

任务路线配置文件为：

```text
src/safe_city_perception/config/mission_plan.yaml
```

完整巡检路线如下：

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

该路线覆盖左侧人群区、上侧垃圾桶区、右侧斑马线区域和下侧楼宇区，并在任务结束后返回起点附近，形成闭环巡检。

### 5.2 控制策略

项目启动 Nav2 栈用于地图、代价地图、规划器和控制器展示，同时在正式演示中使用自研 `patrol_nav_node` 完成稳定闭环巡检。这样做的原因是比赛仿真场地尺度较小，完全依赖 Nav2 局部规划时容易受到代价地图膨胀、目标容差和短距离转弯影响。自研巡检节点能够更精确地控制小车沿既定路线运动，提高录屏稳定性。

巡检控制节点位于：

```text
src/safe_city_perception/safe_city_perception/patrol_nav_node.py
```

控制流程为：

```text
读取路线配置
→ 获取当前机器人位姿
→ 发布 /cmd_vel 前往中继点或任务点
→ 到达任务点后短暂停稳
→ 原地旋转扫描目标
→ 发布区域触发信号
→ 输出识别结果
→ 继续前往下一个任务点
```

为提升稳定性，巡检节点加入了以下机制：

- 基于 `/tf` 与 `/odom` 获取机器人当前位置。
- 基于 `/scan` 进行前方距离判断，遇到近距离障碍自动减速。
- 设置场地软边界，机器人偏离范围时自动回正。
- 到达识别点后进行短时间原地扫描，提高相机对目标的覆盖。
- 任务完成后继续巡航并返回起点附近，形成完整闭环。

## 6. 视觉识别方案

### 6.1 YOLO 主识别

项目当前采用 YOLO 作为主要视觉识别方案。YOLO 节点订阅 `/camera` 图像，加载训练后的权重文件：

```text
models/safe_city_yolo.pt
```

YOLO 配置文件为：

```text
src/safe_city_perception/config/yolo_classes.yaml
```

YOLO 节点文件为：

```text
src/safe_city_perception/safe_city_perception/yolo_detector_node.py
```

YOLO 输出统一发布到：

```text
/safe_city/perception/detections
```

输出 JSON 中包含目标类别、中文名称、目标组、置信度、边界框和识别来源。由于结果汇总节点只关心统一检测话题，YOLO 和 ArUco/OpenCV 可以共用同一套任务汇总链路。

### 6.2 数据集构建与训练

项目原始素材位于仓库根目录：

```text
平安城市/
├── 人偶/
├── 垃圾桶/
└── 楼宇/
```

由于原始素材多为纯净主体图，项目首先使用整图框生成初始训练数据；随后又通过 Gazebo 相机视角自动采集脚本生成更贴近演示场景的训练数据。核心脚本包括：

| 脚本 | 作用 |
|---|---|
| `scripts/prepare_yolo_dataset.py` | 根据原始素材生成 YOLO 数据集骨架 |
| `scripts/capture_gazebo_yolo_dataset.py` | 从 Gazebo 相机画面采集自动标注数据 |
| `scripts/build_formal_yolo_dataset.py` | 合并正式 10 类数据集 |
| `scripts/train_gazebo_yolo_model.sh` | 训练并导出最终 YOLO 权重 |

本轮正式 10 类 YOLO 微调结果如下：

| 指标 | 结果 |
|---|---|
| 验证集图片数 | 30 |
| 验证集实例数 | 772 |
| mAP50 | 0.921 |
| mAP50-95 | 0.811 |

按类别观察，垃圾桶、人群和楼宇类别均已能支撑当前 Gazebo 演示任务。其中火灾楼宇、毒气楼宇、电力故障楼宇等类别受训练样本数量影响，后续仍建议继续补充真实拍摄素材与不同视角图像，提高真实赛场泛化能力。

### 6.3 ArUco/OpenCV 工程兜底

虽然 YOLO 是当前主识别方案，但比赛演示需要考虑工程稳定性。因此系统保留 ArUco 与 OpenCV 颜色识别作为兜底机制：

- 当 YOLO 权重缺失或 `ultralytics` 未安装时，系统仍可启动。
- 当目标短时遮挡或相机角度不佳时，区域级 fallback 可保证终端不会无结果。
- 当后续替换真实训练素材时，旧识别链路可作为调试基线。

ArUco 映射文件为：

```text
src/safe_city_perception/config/aruco_map.yaml
```

当前 ArUco ID 与正式类别映射如下：

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

## 7. 任务汇总与终端展示

结果汇总节点位于：

```text
src/safe_city_perception/safe_city_perception/result_reporter_node.py
```

节点订阅：

```text
/safe_city/perception/detections
/safe_city/task/zone_trigger
```

当机器人到达任务点后，巡检节点发布区域触发消息。结果汇总节点根据 `zone_map.yaml` 过滤当前区域允许的目标，只统计与当前区域相关的类别，避免远处目标或历史检测结果影响终端输出。

为了比赛录屏观感，项目额外编写了干净终端脚本：

```text
scripts/competition_console.py
```

该脚本只订阅任务汇总结果并打印最终识别块，不输出 ROS launch 前缀、Gazebo bridge 日志或调试信息。同时，脚本对中文类别加入白名单，确保终端只显示 10 个正式比赛类别。

一次完整运行的终端输出如下：

```text
RAICOM 平安城市识别结果
等待小车到达识别点...

[人群巡检区]
people: 普通救助人群: 1，医疗救助人群: 1
识别来源: yolo: 2

[垃圾桶巡检区]
trash_bin: 厨余垃圾桶: 1，可回收物垃圾桶: 1，有害垃圾桶: 1，其他垃圾桶: 1
识别来源: yolo: 4

[楼宇巡检区]
building: 坍塌楼宇: 1，火灾楼宇: 1，有毒气体楼宇: 1，电力故障楼宇: 1
识别来源: yolo: 4

[完成] 小车已完成 PDF 地图闭环巡检并返回起点附近
```

## 8. 工程实现与可复现性

项目已整理为 Git 仓库，便于在其他电脑下载运行。为保证仓库体积合理，已将 `build/`、`install/`、`log/`、`runs/`、`datasets/`、`tools/` 等生成文件和本地环境排除，仅保留源码、脚本、文档、原始素材和最终 YOLO 权重。

新电脑运行步骤如下：

```bash
git clone git@github.com:dankingdegou/kobe666.git
cd kobe666/raicom_safe_city_ws
bash scripts/build_workspace.sh
source scripts/use_safe_city_env.sh
bash scripts/run_clean_demo.sh
```

如需无图形界面测试：

```bash
SAFE_CITY_GZ_ARGS="-r -s" bash scripts/run_clean_demo.sh
```

项目脚本已尽量使用相对路径自动定位工作空间，避免固定依赖某一台电脑上的绝对路径，从而提高跨电脑迁移能力。

## 9. 实验验证

### 9.1 构建验证

项目使用如下命令构建：

```bash
bash scripts/build_workspace.sh
```

构建结果：

```text
Summary: 5 packages finished
```

说明 `safe_city_description`、`safe_city_gazebo`、`safe_city_navigation`、`safe_city_perception` 和 `safe_city_bringup` 均能正常编译安装。

### 9.2 仿真运行验证

项目使用无界面模式完成过完整闭环测试：

```bash
SAFE_CITY_GZ_ARGS="-r -s" bash scripts/run_clean_demo.sh
```

验证结果如下：

| 巡检区域 | 输出类别 | 识别来源 |
|---|---|---|
| 人群巡检区 | 普通救助人群: 1，医疗救助人群: 1 | YOLO |
| 垃圾桶巡检区 | 厨余垃圾桶: 1，可回收物垃圾桶: 1，有害垃圾桶: 1，其他垃圾桶: 1 | YOLO |
| 楼宇巡检区 | 坍塌楼宇: 1，火灾楼宇: 1，有毒气体楼宇: 1，电力故障楼宇: 1 | YOLO |

### 9.3 话题与节点验证

关键话题包括：

```text
/camera
/camera_info
/scan
/odom
/tf
/joint_states
/cmd_vel
/safe_city/perception/detections
/safe_city/task/zone_trigger
/safe_city/task/zone_report
/safe_city/task/patrol_state
```

系统运行时，Gazebo 负责发布相机、雷达、里程计等仿真数据；感知节点发布识别结果；巡检节点发布区域触发；结果汇总节点输出每个任务区域的识别统计。

## 10. 项目创新点

本项目的主要创新点和工程亮点如下：

- 面向 RAICOM 平安城市赛题重新构建 4m x 4m 圆角环形正式赛场，而不是使用默认 Gazebo 空场景。
- 对 TurtleBot3 Waffle 风格模型进行二次开发，加入巡检外壳、状态灯和前向 RGB 相机。
- 采用 YOLO 作为主识别方法，避免视觉演示只依赖 ArUco 码，提升识别真实性。
- 将原始纯净主体素材与 Gazebo 相机视角数据结合，快速完成 10 类目标检测模型微调。
- 设计统一 JSON 检测结果接口，使 YOLO、ArUco、OpenCV 兜底结果可以接入同一套任务汇总链路。
- 实现“导航到点、停稳扫描、区域触发、识别统计、继续巡检”的任务闭环。
- 提供干净比赛终端，只输出到点后的识别结果，适合录屏与现场展示。
- 加入类别白名单，保证终端输出严格符合比赛类别要求。
- 保留 Nav2、SLAM Toolbox、地图与代价地图配置，为后续完全 Nav2 化和真实机器人迁移提供基础。

## 11. 不足与改进方向

当前系统已经能够完成省赛阶段核心演示，但仍有以下提升空间：

- 当前正式演示主要采用自研闭环巡检节点，Nav2 主要承担工程展示与后续调优基础。后续可继续优化 Nav2 参数，使机器人完全通过 NavigateToPose 或 FollowWaypoints 完成巡检。
- YOLO 训练素材仍偏少，虽然已能支撑当前 Gazebo 演示，但若迁移到真实赛场，需要补充更多真实拍摄图片、不同视角、不同光照和遮挡样本。
- 当前 Gazebo 目标纹理较规整，后续可增加背景干扰、目标倾斜、部分遮挡和随机光照，提高模型鲁棒性。
- 当前地图主要由脚本生成，后续可加入 SLAM Toolbox 实时建图过程，并将建图过程作为视频展示环节。
- 当前终端输出已经较干净，后续可继续扩展为图形化仪表盘，在 RViz 或网页端展示巡检状态与识别结果。

## 12. 开源工具使用与二次开发说明

项目基于以下开源工具与框架完成：

| 工具/框架 | 用途 |
|---|---|
| ROS 2 Jazzy | 机器人软件框架与节点通信 |
| Gazebo Harmonic | 机器人与赛场仿真 |
| Nav2 | 地图、规划、控制与导航架构展示 |
| SLAM Toolbox | 后续建图展示基础 |
| OpenCV | ArUco 与颜色辅助识别 |
| Ultralytics YOLO | 目标检测模型训练与推理 |
| TurtleBot3 Waffle 风格模型 | 巡检机器人底盘基础 |

团队在开源基础上完成了以下二次开发：

- 自主搭建平安城市正式赛场 world。
- 自主生成赛场目标纹理、任务区标识和巡检模型。
- 修改机器人模型结构，增加平安城市巡检外观与 RGB 相机。
- 配置 ROS-Gazebo bridge，实现仿真传感器与 ROS 2 话题通信。
- 编写巡检控制节点，实现闭环路线巡航、停稳扫描和区域触发。
- 编写 YOLO 检测节点，将深度学习视觉识别接入 ROS 2。
- 编写 ArUco/OpenCV 兜底节点，提高系统容错能力。
- 编写结果汇总与干净终端展示脚本，提高比赛演示观感。
- 整理构建脚本、运行脚本、清理脚本和 Git 仓库，提升项目可复现性。

因此，本项目不是简单运行开源默认 demo，而是在开源机器人与仿真平台基础上完成了面向平安城市赛题的场景、模型、导航、视觉、任务和展示全链路集成。

## 13. 结论

本项目完成了一套基于 ROS 2 Jazzy 与 Gazebo Harmonic 的平安城市智能巡检机器人仿真系统。系统能够在 4m x 4m 正式赛场中完成闭环巡检，依次到达人群、垃圾桶和楼宇巡检区域，并由 YOLO 输出 10 个正式比赛类别中的对应识别结果。项目同时保留 ArUco、OpenCV 与区域先验作为工程兜底机制，使演示链路兼顾真实性与稳定性。

从工程角度看，项目已形成较完整的 ROS 2 多包结构，包含仿真场景、机器人模型、传感器桥接、巡检控制、视觉识别、结果汇总、干净终端输出和可复现运行脚本。当前版本能够支撑省赛阶段的视频展示、技术报告和答辩说明。后续将继续围绕 Nav2 全自动巡检、真实素材扩充、SLAM 建图展示和真实机器人迁移方向进行优化。
