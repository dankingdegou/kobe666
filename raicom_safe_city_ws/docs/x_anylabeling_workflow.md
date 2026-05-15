# X-AnyLabeling 半自动标注流程

本文档说明如何使用 X-AnyLabeling 为 Safe City YOLO 数据集做 AI 预标注和人工校正。

项目地址：

```text
https://github.com/CVHub520/X-AnyLabeling
```

本机已配置源码目录和独立 CPU 运行环境：

```text
/home/twistzz/raicom/tools/X-AnyLabeling
/home/twistzz/raicom/tools/X-AnyLabeling/.venv-cpu
```

检查工具环境：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
bash scripts/check_x_anylabeling.sh
```

当前桌面会话是 X11 时，PyQt6 还需要系统包 `libxcb-cursor0`。如果启动脚本提示缺少该包，请在终端执行一次：

```bash
sudo apt-get install -y libxcb-cursor0
```

该包是 Qt 图形界面依赖，不会影响 ROS 2 工作空间。

## 1. 适合本项目的定位

X-AnyLabeling 可以显著减少手工标注工作量，但不建议把它当成完全无人值守标注工具。原因是当前类别属于比赛专用物料，例如厨余垃圾桶、火灾楼宇、医疗救助人群等，通用模型可能只能给出“桶、建筑、人”这类粗粒度框，细分类别仍需要人工确认。

注意：启动 X-AnyLabeling 只会打开图片目录和类别列表，不会自动框图。自动框图需要在右侧 `Auto Labeling` 面板中选择模型，例如 YOLO11/YOLOv8/GroundingDINO/SAM，然后点击 `Run`；确认单张效果可用后，用 `Ctrl+M` 批量处理所有图片。

推荐定位：

```text
AI 预标注框
→ 人工快速检查类别和边界
→ 导出 YOLO 标签
→ 训练第一版模型
→ 用第一版模型继续自动标注更多截图
→ 人工校正后迭代训练
```

## 2. 准备数据集与类别文件

生成 YOLO 数据集骨架：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
PYTHONNOUSERSITE=1 /usr/bin/python3 scripts/prepare_yolo_dataset.py
```

导出标注工具可用的类别列表：

```bash
PYTHONNOUSERSITE=1 /usr/bin/python3 scripts/export_yolo_labels.py
```

输出文件：

```text
datasets/safe_city_yolo/classes.txt
datasets/safe_city_yolo/labels.txt
datasets/safe_city_yolo/classes_zh.txt
```

`classes.txt` 和 `labels.txt` 是英文类别名，一行一个类别，顺序与 `data.yaml` 保持一致。`classes_zh.txt` 用于人工核对中文含义。

## 3. 在 X-AnyLabeling 中标注

建议按以下方式操作：

1. 如果你要继续扩充更复杂的截图，再启动训练集标注：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
bash scripts/launch_x_anylabeling_train.sh
```

2. 再启动验证集标注：

```bash
cd /home/twistzz/raicom/raicom_safe_city_ws
bash scripts/launch_x_anylabeling_val.sh
```

3. 如果手动打开 X-AnyLabeling，则打开 `datasets/safe_city_yolo/images/train`，并加载类别列表 `datasets/safe_city_yolo/classes.txt`。
4. 对于更复杂的新图，用内置 AI 模型进行预标注；对于你当前这种单主体纯净图，直接用整图框作为第一版数据就足够先把训练链路跑通。
5. 逐张检查边界框是否完整覆盖目标，类别是否正确。
6. 将标签保存或导出为 YOLO 格式。
7. 对 `datasets/safe_city_yolo/images/val` 重复同样流程。

如果只是想零人工快速验证 YOLO 训练链路，可以生成全图框 baseline：

```bash
bash scripts/bootstrap_yolo_full_boxes.sh
```

该脚本会把每张图片整幅图作为目标框，只能用于冒烟测试，不适合作为正式训练标签。

导出的标签应放在：

```text
datasets/safe_city_yolo/labels/train
datasets/safe_city_yolo/labels/val
```

每张图片对应一个同名 `.txt` 标签文件。例如：

```text
images/train/kitchen_bin_IMG_1.jpg
labels/train/kitchen_bin_IMG_1.txt
```

YOLO 标签格式：

```text
class_id center_x center_y width height
```

其中坐标均为 0 到 1 之间的归一化比例。

## 4. 训练与迭代

确认标签不为空后训练：

```bash
scripts/train_yolo_model.sh
```

训练完成后权重会复制到：

```text
models/safe_city_yolo.pt
```

完整演示会自动尝试加载该模型：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py
```

如果要使用其他权重：

```bash
ros2 launch safe_city_bringup mission_nav2_demo.launch.py yolo_model:=/absolute/path/to/best.pt
```

## 5. 质量检查标准

- 每个类别至少有若干张非空标签，不能只有人偶类或只垃圾桶类。
- 训练集和验证集都要有标签，验证集为空会导致评估失真。
- 框要覆盖完整目标，不要只框文字、颜色块或局部贴纸。
- 同一张图如果有多个目标，应标多个框。
- 类别顺序必须与 `datasets/safe_city_yolo/data.yaml` 的 `names` 顺序一致。

现有原始素材只有 20 张，适合做第一版小模型或流程验证。正式比赛前建议继续采集 Gazebo 相机视角截图，每类至少扩展到 50 张以上。
