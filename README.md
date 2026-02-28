# Pano Dataset Scripts
用于创建与AGD20K格式相同的数据集辅助脚本.
输入格式:
```text
input/
  object_001.jpg(RGB),
  object_001.json(Polygon/Dots format labeled),
  ...
```
输出格式:
```text
dataset_root/
  Seen/
    testset/
      egocentric/
        sit/chair/chair_001.jpg
      GT/
        sit/chair/chair_001.png
```
本仓库有 4 个主脚本：

1. `pipeline.py`: 标注 JSON -> 中间结果(polygon-shrinked polygon-dots) + mask + 叠加可视化
2. `png2npy.py`: mask PNG -> 训练用 `.npy`
3. `visualize_npy.py`: 检查 `.npy` 通道内容
4. `util/reorganize_pipeline_output.py`: 将 pipeline 输出整理成 `dataset/Seen|Unseen/testset/...` 结构

## 目录与路径规范

所有的 affordance 和 object 信息存储在 `util/data.py` 的列表中。示例如下:

`BASE_OBJ = ['lamp', 'armset', 'backrest', 'bathtub', 'bed', 'cabinet_door', 'door', 'drawer',
             'garbage', 'microwave', 'mirror', 'pillow', 'refrigerator', 'screen', 'sink', 'seat',
             'stairway', 'table', 'window']`

`SEEN_AFF = ['light', 'swing_open', 'lie', 'sit', 'rest_arm', 'lean_back', 'climb',
             'wash', 'drop', 'display', 'lying_on', 'bathe', 'place', 'look_through', 'reflect_image',
             'open', 'heating', 'pull', 'refrigerate']`

需要注意的是，`OBJ` 列表和 `AFF` 列表中的元素内容需要一一对应。例如，`lamp` 对应的 affordance 为 `light`，则
`BASE_OBJ[0]='lamp', SEEN_AFF[0]='light'`。

## 1 pipeline.py

### 用途

从 Labelme 多边形标注的 JSON 出发，执行：

- `json-shrink`
- `json-convert`（polygon -> points）
- `json-png`（points -> gaussian mask）
- `mask-viz`（RGB + mask 叠加）

### 示例

```bash
python pipeline.py run --input <input_dir> --output <output_dir> --distance 50 --spacing 2
```

### 输入格式（示例）

```text
input_dir/
  chair_001.jpg
  chair_001.json
  table_010.jpg
  table_010.json
```

### 期望输出结构

```text
output_dir/
  Shrinked/
    chair_001.json
    table_010.json
  Spotted/
    chair_001.json
    table_010.json
  GT/
    chair_001.png
    table_010.png
  Vis/
    chair_001_vis.png
    table_010_vis.png
  Shrink_config.json
```

说明：

- `Shrinked`: shrink 后 JSON
- `Spotted`: 点阵 JSON
- `GT`: mask PNG（单通道）
- `Vis`: 叠加可视化 PNG
- `Shrink_config.json`: 每个 JSON 的 shrink 参数记录
- 可以通过修改额外的参数例如sigma和min-area-ratio来控制高热度区域的大小.

## 2 png2npy.py

### 用途

将 `GT` 中的每个 PNG mask 转为训练用 `.npy`，并按 `util/data.py` 的 `BASE_OBJ -> SEEN_AFF` 映射写入通道。

### 示例

```bash
python png2npy.py --png_folder <gt_root> --output_npy_dir <npy_root>
```

### 输入要求

- 递归读取 `--png_folder` 下所有 `.png`
- 文件名（不含后缀）应可映射到对象名（通过 `util/data.py`）

### 期望输出结构

输出会保留输入相对路径层级：

```text
npy_root/
  chair_001.npy
  table_010.npy
```

如果输入有子目录，也会镜像子目录：

```text
gt_root/
  a/chair_001.png
  b/table_010.png

npy_root/
  a/chair_001.npy
  b/table_010.npy
```

### `.npy` 格式

- shape: `(C, H, W)`（通道优先）,其中H,W可以通过参数修改
- dtype: `float32`
- `C` 为 affordance 通道数（默认来自 `SEEN_AFF`）
- 通道顺序与 `util/data.py` 中 `SEEN_AFF` 一致

## 3 visualize_npy.py

### 用途

可视化 `.npy` 的各通道内容，并打印每通道非零占比与最大值，便于检查标签是否写入正确通道。

### 示例

```bash
python visualize_npy.py --npy_dir <npy_root>
```

保存可视化图到目录：

```bash
python visualize_npy.py --npy_dir <npy_root> --save_dir <viz_root>
```

限制只看前 N 个：

```bash
python visualize_npy.py --npy_dir <npy_root> --max_files 10
```

### 输出形式

- 终端输出：文件 shape/dtype/range + 各通道统计
- 图像标题：`channel_index: affordance_name`
- 若使用 `--save_dir`，输出为与 `.npy` 相对路径一致的 `.png` 可视化图

## 4 reorganize_pipeline_output.py

### 用途

将 `pipeline.py` 的 `GT` 输出整理成：

```text
dataset/
  Seen|Unseen/
    testset/
      egocentric/<aff>/<object>/<name>.jpg
      GT/<aff>/<object>/<name>.png
```

其中：

- `GT` 来自 `pipeline_output/GT`
- `egocentric` 从 `--rgb_dir` 复制 RGB
- `Seen/Unseen` 与 `aff` 来自 `util/data.py` 映射

### 示例

```bash
python util/reorganize_pipeline_output.py \
  --pipeline_output <pipeline_output_dir> \
  --dataset_root <dataset_root> \
  --rgb_dir <input_rgb_dir>
```

### 期望输出结构（示例）

```text
dataset_root/
  Seen/
    testset/
      egocentric/
        sit/chair/chair_001.jpg
      GT/
        sit/chair/chair_001.png
```

说明：

- 若对象在 `NOVEL_OBJ` 中，则会进入 `Unseen/testset/...`
- 未映射对象会跳过并打印 `[SKIP]`
