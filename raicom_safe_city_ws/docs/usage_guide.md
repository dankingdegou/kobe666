# RAICOM 平安城市项目使用流程

本文档说明如何在当前工作空间中构建、启动和验证 RAICOM 2026 平安城市巡检机器人仿真系统。

当前技术栈：

```text
Ubuntu 24.04
ROS 2 Jazzy
Gazebo Harmonic
Nav2
SLAM Toolbox
OpenCV / ArUco
YOLO
TurtleBot3 Waffle 派生巡检底盘
```

## 1. 项目结构

```text
raicom_safe_city_ws/
├── scripts/
│   ├── build_workspace.sh          # 推荐构建脚本
│   ├── use_safe_city_env.sh        # 推荐环境加载脚本
│   ├── generate_aruco_boards.py    # ArUco 识别牌生成脚本
│   ├── generate_formal_safe_city_world.py # PDF 示意图风格正式赛场 world 生成脚本
│   ├── generate_safe_city_map.py   # 4m x 4m 导航地图生成脚本
│   ├── prepare_yolo_dataset.py     # YOLO 数据集骨架生成脚本
│   ├── export_yolo_labels.py       # 标注工具类别列表导出脚本
│   ├── launch_x_anylabeling_train.sh # 启动训练集半自动标注
│   ├── launch_x_anylabeling_val.sh # 启动验证集半自动标注
│   └── train_yolo_model.sh         # YOLO 训练脚本
├── src/
│   ├── safe_city_bringup/          # 总启动 launch
│   ├── safe_city_description/      # 机器人模型相关文件
│   ├── safe_city_gazebo/           # Gazebo world、模型、仿真启动
│   ├── safe_city_navigation/       # Nav2、SLAM、地图、导航点
│   └── safe_city_perception/       # ArUco 识别、巡检任务、结果输出
└── docs/
    ├── usage_guide.md              # 本文件
    ├── report/
    ├── ppt/
    └── video/
```

## 2. 每次打开新终端后的准备

进入工作空间：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
```

加载项目环境：

```bash
source /home/twistzz/raicom/raicom_safe_city_ws/scripts/use_safe_city_env.sh
```

注意：不要直接 `source /opt/ros/jazzy/setup.bash` 后就启动项目。当前机器曾出现 Python 用户环境污染和 `set -u` 导致的环境变量问题，推荐统一使用上面的脚本。

如果刚才已经启动过 Gazebo 或 Nav2，建议先清理残留进程，避免多个 `/clock`、`/tf` 源同时存在导致小车跑偏：

```bash
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/clean_safe_city_runtime.sh
```

## 3. 构建项目

推荐使用项目自带脚本：

```bash
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/build_workspace.sh
```

构建成功时应看到类似输出：

```text
Summary: 5 packages finished
```

构建完成后，重新加载环境：

```bash
source /home/twistzz/raicom/raicom_safe_city_ws/scripts/use_safe_city_env.sh
```

## 4. 一键启动完整巡检演示

这是目前最重要的演示命令：

```bash
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/run_clean_demo.sh
```

这个命令是比赛/录屏优先模式：默认会打开 Gazebo 图形界面，Gazebo 与 ROS 日志会写入 `log/competition_demo/`，终端只在小车到达识别点后打印识别结果，避免 launch 前缀、bridge 日志、Nav2 日志影响观感。

如果需要调试完整 ROS 输出，再使用普通 launch：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

普通 launch 默认也会打开 Gazebo 图形界面。如果只想后台运行仿真，可以使用：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py gz_args:="-r -s"
```

干净演示脚本如果也想后台无界面运行，可以这样设置：

```bash
SAFE_CITY_GZ_ARGS="-r -s" bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/run_clean_demo.sh
```

该 launch 会同时启动：

```text
Gazebo Harmonic 正式赛场 world
ROS-Gazebo bridge
机器人传感器话题
Nav2 / map_server / planner / controller
ArUco 识别节点
巡检任务节点
结果汇总输出节点
```

当前演示流程：

```text
起点
→ 左侧环形通道入口
→ 人群巡检区
→ 左上弯道
→ 垃圾桶巡检区
→ 右上弯道
→ 右侧上斑马线
→ 右侧下斑马线
→ 右下弯道
→ 楼宇巡检区
→ 左下弯道
→ 回到起点附近
→ 终端输出总巡检结果
```

成功时终端会出现类似结果：

```text
RAICOM 平安城市识别结果
等待小车到达识别点...

[人群巡检区]
people: 医疗救助人群: 1，普通救助人群: 1
识别来源: yolo: 2

[垃圾桶巡检区]
trash_bin: 其他垃圾桶: 1，厨余垃圾桶: 1，可回收物垃圾桶: 1，有害垃圾桶: 1
识别来源: yolo: 4

[楼宇巡检区]
building: 坍塌楼宇: 1，有毒气体楼宇: 1，火灾楼宇: 1，电力故障楼宇: 1
识别来源: yolo: 4

[完成] 小车已完成 PDF 地图闭环巡检并返回起点附近
```

说明：当前机器人模型已升级为 TurtleBot3 Waffle 派生巡检底盘，保留差速驱动、轮式底盘、顶部激光雷达、RGB 相机、里程计和 TF，并增加平安城市巡检外壳与状态灯，便于在报告中说明“开源模型二次开发”。巡检节点默认启用了带激光雷达安全保护的 `simple_navigation` 闭环巡航模式，通过 `/tf` 获取车体位姿、通过 `/scan` 做前方减速和越界回场保护，并通过 `/cmd_vel` 控制底盘。Nav2 栈仍会启动，用于展示地图、代价地图、规划器配置和后续正式导航调优。

当前正式赛场 world 已按 PDF 示意图重构为 4m x 4m 圆角环形跑道，包含外边界、内边界、约 800mm 通道、右侧斑马线区域、垃圾桶区、人群区和楼宇区。视觉链路已升级为 YOLO 主识别 + ArUco/OpenCV/区域先验兜底；当前稳定演示中三大巡检区域均由 YOLO 输出，终端识别结果严格收敛到 10 个正式比赛类别。

重要说明：YOLO 是当前演示的主识别来源，ArUco、颜色识别和区域先验只作为工程容错机制保留。当 YOLO 权重缺失、模型未加载或短时视角遮挡导致目标未检出时，系统才会启用兜底链路，避免比赛录屏中断。

## 5. 单独启动 Gazebo 仿真

如果只想看场地、机器人、相机、雷达和里程计：

```bash
ros2 launch safe_city_gazebo camera_sim.launch.py
```

启动后可以检查话题：

```bash
ros2 topic list
```

关键话题应包括：

```text
/camera
/camera_info
/scan
/odom
/tf
/joint_states
/cmd_vel
```

当前主要坐标系：

```text
map
odom
base_footprint
base_link
base_scan
camera_link
```

其中 `base_scan` 对应顶部二维激光雷达，`camera_link` 对应前向 RGB 相机。

检查频率：

```bash
ros2 topic hz /camera
ros2 topic hz /scan
ros2 topic hz /odom
```

手动控制机器人前进：

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.12}, angular: {z: 0.0}}" --rate 10
```

手动控制机器人旋转：

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.6}}" --rate 10
```

停止机器人：

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}" --once
```

## 6. 单独启动视觉识别

先启动 Gazebo：

```bash
ros2 launch safe_city_gazebo camera_sim.launch.py
```

再开一个新终端：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
source /home/twistzz/raicom/raicom_safe_city_ws/scripts/use_safe_city_env.sh
ros2 launch safe_city_perception perception.launch.py
```

识别结果话题：

```bash
ros2 topic echo /safe_city/perception/detections
```

ArUco ID 映射：

```text
1: 厨余垃圾桶
2: 可回收物垃圾桶
3: 有害垃圾桶
4: 其他垃圾桶
5: 医疗救助人群
6: 普通救助人群
7: 普通救助人群
8: 坍塌楼宇
9: 火灾楼宇
10: 有毒气体楼宇
11: 电力故障楼宇
```

配置文件位置：

```text
src/safe_city_perception/config/aruco_map.yaml
src/safe_city_perception/config/zone_map.yaml
```

## 7. 地图与导航相关命令

导航地图文件：

```text
src/safe_city_navigation/maps/safe_city_map.yaml
src/safe_city_navigation/maps/safe_city_map.pgm
```

重新生成 4m x 4m 导航地图：

```bash
/home/twistzz/raicom/raicom_safe_city_ws/scripts/generate_safe_city_map.py
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/build_workspace.sh
```

重新生成 PDF 示意图风格正式赛场 world：

```bash
source /home/twistzz/raicom/raicom_safe_city_ws/scripts/use_safe_city_env.sh
python3 /home/twistzz/raicom/raicom_safe_city_ws/scripts/generate_formal_safe_city_world.py
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/build_workspace.sh
```

Nav2 参数文件：

```text
src/safe_city_navigation/config/nav2_params.yaml
```

巡检点文件：

```text
src/safe_city_navigation/config/waypoints.yaml
```

任务路线文件：

```text
src/safe_city_perception/config/mission_plan.yaml
```

如果只启动 Nav2：

```bash
ros2 launch safe_city_navigation nav2.launch.py
```

通常更推荐直接用完整演示 launch：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

## 8. 常用验证命令

查看节点：

```bash
ros2 node list
```

查看话题：

```bash
ros2 topic list
```

查看 action：

```bash
ros2 action list
```

查看 `/cmd_vel`：

```bash
ros2 topic echo /cmd_vel
```

查看 `/odom`：

```bash
ros2 topic echo /odom
```

查看雷达频率：

```bash
ros2 topic hz /scan
```

查看相机频率：

```bash
ros2 topic hz /camera
```

生成 TF 树：

```bash
ros2 run tf2_tools view_frames
```

## 9. 录制比赛视频建议

推荐录制顺序：

```text
1. 打开 Gazebo，展示 4m x 4m 平安城市场地
2. 展示机器人模型、相机、雷达、/cmd_vel、/odom、/scan
3. 展示完整巡检过程
4. 展示终端中垃圾桶、人群、楼宇识别结果
5. 展示代码结构和关键配置文件
```

推荐录屏命令：

```bash
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/run_clean_demo.sh
```

视频里建议同时露出：

```text
Gazebo 场景
终端巡检日志
必要时打开 RViz2 展示 TF / LaserScan / Map
```

## 10. 常见问题处理

### 10.1 `AMENT_TRACE_SETUP_FILES: 未绑定的变量`

使用项目环境脚本，不要手动硬 source：

```bash
source /home/twistzz/raicom/raicom_safe_city_ws/scripts/use_safe_city_env.sh
```

### 10.2 找不到包或 launch 文件

先重新构建并加载环境：

```bash
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/build_workspace.sh
source /home/twistzz/raicom/raicom_safe_city_ws/scripts/use_safe_city_env.sh
```

### 10.3 Gazebo 或 ROS 进程残留

如果重复启动后话题异常、仿真卡住，可以清理残留进程：

```bash
bash /home/twistzz/raicom/raicom_safe_city_ws/scripts/clean_safe_city_runtime.sh
```

然后重新启动：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

### 10.4 识别结果不完整

当前识别优先级为 YOLO > ArUco > OpenCV 颜色识别 > 区域目标清单兜底。若某类目标没有输出，优先检查：

```text
1. Gazebo 中对应目标牌是否被机器人相机看到
2. /camera 是否有图像
3. /safe_city/perception/detections 是否持续发布
4. zone_map.yaml 中 allowed_marker_ids 是否包含对应 ID
5. aruco_map.yaml 中 ID 映射是否正确
6. zone_map.yaml 中 fallback_marker_ids 是否配置了该区域的兜底目标
```

### 10.5 机器人不动

检查 `/cmd_vel` 是否有数据：

```bash
ros2 topic echo /cmd_vel
```

检查 `/odom` 是否更新：

```bash
ros2 topic echo /odom
```

手动发速度测试：

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.12}, angular: {z: 0.0}}" --rate 10
```

如果手动速度能动，而完整演示不动，检查：

```text
src/safe_city_perception/launch/mission_nav2.launch.py
```

确认 `patrol_nav_node` 参数中：

```text
simple_navigation: True
simulate_navigation: False
```

## 11. 推荐开发顺序

后续继续优化时，建议按这个顺序推进：

```text
1. 保持 mission_nav2_demo 能稳定完整跑完
2. 调整 world 中目标牌、垃圾桶、人群、楼宇的摆放
3. 优化 ArUco 识别稳定性
4. 完善 RViz2 展示配置
5. 继续调 Nav2 正式自主导航参数
6. 整理报告、PPT、视频脚本
```

不要在比赛前直接大改所有模块。优先保证完整演示链路稳定，然后再逐步替换更高级的导航或识别方案。
