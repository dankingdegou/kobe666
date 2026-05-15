# RAICOM 2026 平安城市巡检机器人

这是 RAICOM 2026 全域安防/平安城市赛题的 ROS 2 + Gazebo 仿真项目。当前版本已经包含正式赛场 world、巡检小车、闭环巡检路线、YOLO 视觉识别、ArUco/OpenCV 兜底链路和干净比赛终端输出。

## 当前效果

干净演示命令会打开 Gazebo 图形界面，并且终端只在小车到达识别点后打印结果：

```bash
cd raicom_safe_city_ws
bash scripts/run_clean_demo.sh
```

当前稳定输出为 YOLO 主识别：

```text
[人群巡检区]
people: 普通救助人群: 1，医疗救助人群: 1
识别来源: yolo: 2

[垃圾桶巡检区]
trash_bin: 厨余垃圾桶: 1，可回收物垃圾桶: 1，有害垃圾桶: 1，其他垃圾桶: 1
识别来源: yolo: 4

[楼宇巡检区]
building: 坍塌楼宇: 1，火灾楼宇: 1，有毒气体楼宇: 1，电力故障楼宇: 1
识别来源: yolo: 4
```

终端识别结果被限制为 10 个正式类别：普通救助人群、医疗救助人群、厨余垃圾桶、可回收物垃圾桶、有害垃圾桶、其他垃圾桶、坍塌楼宇、火灾楼宇、有毒气体楼宇、电力故障楼宇。

## 推荐环境

```text
Ubuntu 24.04
ROS 2 Jazzy
Gazebo Harmonic
Nav2
SLAM Toolbox
OpenCV / ArUco
Ultralytics YOLO
```

## 新电脑快速运行

1. 克隆仓库：

```bash
git clone git@github.com:dankingdegou/kobe666.git
cd kobe666/raicom_safe_city_ws
```

2. 安装 ROS 2 Jazzy、Gazebo Harmonic、Nav2、SLAM Toolbox 等依赖后，构建工作空间：

```bash
bash scripts/build_workspace.sh
source scripts/use_safe_city_env.sh
```

3. 启动干净比赛演示：

```bash
bash scripts/run_clean_demo.sh
```

如果只是服务器/无显示环境测试：

```bash
SAFE_CITY_GZ_ARGS="-r -s" bash scripts/run_clean_demo.sh
```

## 重要目录

```text
raicom_safe_city_ws/src/       ROS 2 源码包
raicom_safe_city_ws/scripts/   构建、运行、训练、数据集脚本
raicom_safe_city_ws/docs/      使用说明、YOLO 流程、技术报告
raicom_safe_city_ws/models/    当前最终 YOLO 权重
平安城市/                      原始训练素材
```

完整使用说明见：

```text
raicom_safe_city_ws/docs/usage_guide.md
raicom_safe_city_ws/docs/yolo_workflow.md
```
