#!/bin/bash

#   参数：                                                                                                                                                          
#   1. 输入目录（默认 ../data/source/armset）                                                                                                                               
#   2. 输出目录（默认 ../data/tobeprocess）                                                                                                                               
#   3. 点间距 s（默认 1）                                                                                                                                           
#   4. 核缩放 k（默认 1.0）                                                                                                                                         
                                                                                                                                                                
#   输出结构：                                                                                                                                                      
#   <输出目录>/                                                                                                                                                     
#   ├── json_points/   # 转换后的json                                                                                                                               
#   └── masks/         # 掩码png图

INPUT_DIR=${1:-"../data/source/armset"}
OUTPUT_DIR=${2:-"../data/tobeprocess"}
SPACING=${3:-1}
KERNEL_SCALE=${4:-1.0}

SCRIPT_DIR="/root/autodl-tmp/OOAL/utils"

python "${SCRIPT_DIR}/convert_polygon_to_points.py" -i "$INPUT_DIR" -o "${OUTPUT_DIR}/json_points" -s "$SPACING"
python "${SCRIPT_DIR}/generate_gaussian_mask.py" -i "${OUTPUT_DIR}/json_points" -o "${OUTPUT_DIR}/masks" -k "$KERNEL_SCALE"

