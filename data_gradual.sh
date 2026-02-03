#!/bin/bash

#   参数：
#   1. 输入目录（默认 ../data/source/window）
#   2. 输出目录（默认 ../data/tobeprocess/gradual4）
#   3. 内部点间距（默认 1）
#   4. 外部点间距（默认 3）
#   5. 过渡区域占比（默认 0.3）
#   6. 边缘排除距离（默认 5.0，像素）
#   7. 高斯核缩放（默认 150）

INPUT_DIR=${1:-"/root/autodl-tmp/OOAL/data/source/window"}
OUTPUT_DIR=${2:-"/root/autodl-tmp/OOAL/data/tobeprocess/gradual3"}
INNER_SPACING=${3:-1}
OUTER_SPACING=${4:-3}
TRANSITION=${5:-0.3}
EDGE_EXCLUSION=${6:-5.0}
KERNEL_SCALE=${7:-150}

SCRIPT_DIR="/root/autodl-tmp/OOAL/utils"

# python "${SCRIPT_DIR}/convert_polygon_to_points_gradual.py" \
#     -i "$INPUT_DIR" \
#     -o "${OUTPUT_DIR}/json_points" \
#     -s "$INNER_SPACING" \
#     -os "$OUTER_SPACING" \
#     -t "$TRANSITION" \
#     -e "$EDGE_EXCLUSION"

python "${SCRIPT_DIR}/generate_gaussian_mask.py" \
    -i "${OUTPUT_DIR}/json_points" \
    -o "${OUTPUT_DIR}/masks" \
    -k "$KERNEL_SCALE"