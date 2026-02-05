#!/bin/bash

# ==============================================================================
# 数据处理管道脚本
# ==============================================================================
# 功能: 自动化处理多边形标注数据的完整流水线
# 
# 处理步骤:
#   1. 缩放多边形 (suoxiao.py)          - 将原始多边形按比例缩小
#   2. 转换为点阵 (convert_polygon_to_points.py) - 将多边形转换为密集点阵
#   3. 生成高斯掩码 (generate_gaussian_mask.py)  - 基于点阵生成高斯掩码图
#
# 用法:
#   ./data.sh [输入目录] [输出目录] [点间距] [核缩放]
#
# 参数:
#   $1: INPUT_DIR     - 输入目录 (默认: ./data/source)
#   $2: OUTPUT_DIR    - 输出目录 (默认: ./data/temps)  
#   $3: SPACING       - 点间距 (默认: 1)
#   $4: KERNEL_SCALE  - 高斯核缩放因子 (默认: 50)
#
# 示例:
#   ./data.sh                                    # 使用默认参数
#   ./data.sh ../data/source ./output 0.8 40    # 自定义参数
# ==============================================================================

INPUT_DIR=${1:-"/root/autodl-tmp/OOAL/data/source"}
OUTPUT_DIR=${2:-"/root/autodl-tmp/OOAL/data/temps/3"}
SHRINK_DISTANCE=${3:- 50}
SPACING=${4:- 1}
KERNEL_SCALE=${5:- 50}

SCRIPT_DIR="/root/autodl-tmp/OOAL/utils/data_process"

echo "Start Shrinking polygons."
python $SCRIPT_DIR/shrink_polygon.py --input "$INPUT_DIR" --output "${OUTPUT_DIR}/Shrinked" --distance $SHRINK_DISTANCE 

echo "Start Converting polygons to dense points."
python $SCRIPT_DIR/convert_polygon_to_points.py --input "${OUTPUT_DIR}/Shrinked" --output "${OUTPUT_DIR}/Spotted" --spacing $SPACING

echo "Start Generating Gaussian masks."
python $SCRIPT_DIR/generate_gaussian_mask.py --input "${OUTPUT_DIR}/Spotted" --output "${OUTPUT_DIR}/GT" --kernel-scale $KERNEL_SCALE --spacing $SPACING



