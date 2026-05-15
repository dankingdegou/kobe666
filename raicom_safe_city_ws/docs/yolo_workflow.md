# Safe City YOLO 视觉升级流程

本文档说明如何把 YOLO 接入当前 Gazebo 平安城市巡检演示，并用 Gazebo 相机画面自动生成训练数据。

## 1. 当前类别

YOLO 类别配置位于：

```text
src/safe_city_perception/config/yolo_classes.yaml
```

当前模型输出严格限制为 10 个正式比赛类别：

```text
kitchen_bin
recyclable_bin
hazardous_bin
other_bin
collapse_building
fire_building
toxic_gas_building
power_failure_building
medical_rescue_person
normal_rescue_person
```

终端允许出现的中文识别结果只有：

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

说明：Gazebo 内部颜色目标会被映射成正式类别，例如青色人偶输出为医疗救助人群，黄色/洋红人偶输出为普通救助人群。

## 2. 生成数据集骨架

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
PYTHONNOUSERSITE=1 /usr/bin/python3 scripts/prepare_yolo_dataset.py
```

输出目录：

```text
datasets/safe_city_yolo/
├── data.yaml
├── images/train
├── images/val
├── labels/train
└── labels/val
```

默认生成空标签文件，表示仍需人工标注。对于你当前这批“纯净主体图”，其实可以先不手工框，直接用整图框做第一版训练。

本项目也准备了 X-AnyLabeling 半自动标注流程，可用 AI 预标注减少手动画框工作量，适合后续扩充素材时继续迭代：

```text
docs/x_anylabeling_workflow.md
```

本机已配置 X-AnyLabeling，可直接启动：

```bash
bash scripts/launch_x_anylabeling_train.sh
bash scripts/launch_x_anylabeling_val.sh
```

如果只是想快速验证训练链路，或者当前素材本身就是单主体纯净图，可以直接使用：

```bash
PYTHONNOUSERSITE=1 /usr/bin/python3 scripts/prepare_yolo_dataset.py --bootstrap-full-box
```

注意：`--bootstrap-full-box` 会把整张图当成目标框，只适合链路冒烟测试，不适合作为正式比赛识别模型。

也可以直接运行封装脚本：

```bash
bash scripts/bootstrap_yolo_full_boxes.sh
```

## 2.1 自动采集 Gazebo 相机训练集

当前更推荐使用 Gazebo 相机视角训练集，因为它和演示时 `/camera` 图像域一致。启动一次无界面完整巡检，再运行自动标注采集：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
source scripts/use_safe_city_env.sh
ros2 launch safe_city_bringup mission_nav2_demo.launch.py gz_args:="-r -s" clean_output:=false log_level:=error
```

另开一个终端：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
source scripts/use_safe_city_env.sh
python3 scripts/capture_gazebo_yolo_dataset.py --max-images 260 --max-seconds 150 --sample-every 4 --min-area 120
```

输出目录：

```text
datasets/safe_city_gazebo_yolo/
├── data.yaml
├── images/train
├── images/val
├── labels/train
└── labels/val
```

该脚本通过当前仿真目标的颜色特征自动生成 YOLO 框，主要用于把模型快速迁移到 Gazebo 相机视角。它不是替代真实比赛素材标注的最终方案，但比纯主体整图框更适合当前 demo。

## 3. 训练模型

训练脚本：

```bash
scripts/train_yolo_model.sh
```

默认读取：

```text
datasets/safe_city_yolo/data.yaml
```

训练完成后会尝试复制最优权重到：

```text
models/safe_city_yolo.pt
```

如果当前 Python 环境没有 `ultralytics`，需要先安装到训练环境中。项目运行环境建议继续使用 `/usr/bin/python3` 和 `PYTHONNOUSERSITE=1`，避免用户目录下的 NumPy/OpenCV 版本污染 ROS 2 节点。

针对 Gazebo 自动采集数据和原始纯净主体素材合并后的正式 10 类数据集，使用：

```bash
BASE_MODEL=/home/twistzz/raicom/raicom_safe_city_ws/yolo11n.pt EPOCHS=35 RUN_NAME=safe_city_yolo_formal_full bash scripts/train_gazebo_yolo_model.sh
```

训练完成后会覆盖：

```text
models/safe_city_yolo.pt
```

本轮正式 10 类 YOLO 微调结果：

```text
验证集图片: 30
验证集实例: 772
mAP50: 0.921
mAP50-95: 0.811
```

## 4. ROS 2 接入

YOLO 节点文件：

```text
src/safe_city_perception/safe_city_perception/yolo_detector_node.py
```

节点订阅：

```text
/camera
```

节点发布：

```text
/safe_city/perception/detections
```

输出 JSON 与 ArUco 节点保持兼容，因此 `result_reporter_node` 和 `mission_coordinator_node` 不需要推倒重写。

完整演示 launch 已并行启动 YOLO 与 ArUco：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

如需指定模型：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py yolo_model:=/absolute/path/to/best.pt
```

当模型文件不存在或未安装 `ultralytics` 时，YOLO 节点会输出警告并空转，不影响 ArUco 兜底演示。

比赛干净演示命令：

```bash
bash scripts/run_clean_demo.sh
```

当前验证通过的输出中，三大区域均由 YOLO 接管：

```text
[人群巡检区]
people: 医疗救助人群: 1，普通救助人群: 1
识别来源: yolo: 2

[垃圾桶巡检区]
trash_bin: 其他垃圾桶: 1，厨余垃圾桶: 1，可回收物垃圾桶: 1，有害垃圾桶: 1
识别来源: yolo: 4

[楼宇巡检区]
building: 坍塌楼宇: 1，有毒气体楼宇: 1，火灾楼宇: 1，电力故障楼宇: 1
识别来源: yolo: 4
```

## 5. 推荐数据增强方向

现有原始素材只有 20 张，不足以训练稳定模型。建议优先补充：

- Gazebo 相机视角截图，覆盖远、中、近距离。
- 每类目标不同朝向和遮挡情况。
- 不同光照、背景、赛道位置。
- 每类至少 50 张以上，正式冲刺建议 100 张以上。

最终报告中建议表述为：系统采用 YOLO 作为主要视觉识别方法，并保留 ArUco/区域先验作为工程容错机制，以兼顾识别真实性与比赛演示稳定性。
