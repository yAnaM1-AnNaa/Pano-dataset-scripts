#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据处理管道脚本
演示如何在不同脚本间传递参数，避免使用global变量
支持配置文件和命令行参数
"""

import json
import os
import argparse
from dataclasses import dataclass
from typing import Optional

# 导入其他处理脚本的函数
try:
    from suoxiao import process_directory_recursive as scale_polygons
    from convert_polygon_to_points import process_folder as convert_to_points  
    from generate_gaussian_mask import process_folder as generate_masks
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有处理脚本都在同一目录下")


@dataclass
class PipelineConfig:
    """管道配置类"""
    # 输入输出路径
    input_folder: str = './input'
    output_folder: str = './output'
    
    # 处理参数
    scale_factor: float = 0.4        # 多边形缩放比例
    spacing: float = 0.8             # 点间距
    kernel_scale: float = 50.0       # 高斯核缩放
    default_spacing: int = 1         # 默认点间距
    
    # 中间步骤输出路径（可选）
    scaled_output: Optional[str] = None
    points_output: Optional[str] = None
    
    @classmethod
    def from_json(cls, config_path: str) -> 'PipelineConfig':
        """从JSON文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)
    
    def save_to_json(self, config_path: str):
        """保存配置到JSON文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, indent=2, ensure_ascii=False)


def run_pipeline_step1_scale(config: PipelineConfig) -> str:
    """步骤1: 缩放多边形"""
    print("=" * 50)
    print("步骤1: 缩放多边形")
    print("=" * 50)
    
    # 确定输出路径
    output_path = config.scaled_output or os.path.join(config.output_folder, 'step1_scaled')
    
    # 调用缩放函数，传递参数
    success, error = scale_polygons(
        input_dir=config.input_folder,
        output_dir=output_path,
        scale_factor=config.scale_factor
    )
    
    print(f"缩放完成: 成功 {success} 个, 失败 {error} 个")
    return output_path


def run_pipeline_step2_convert(config: PipelineConfig, input_path: str) -> str:
    """步骤2: 转换为点阵"""
    print("=" * 50)
    print("步骤2: 转换为点阵")
    print("=" * 50)
    
    # 确定输出路径
    output_path = config.points_output or os.path.join(config.output_folder, 'step2_points')
    
    # 调用转换函数，传递spacing参数
    convert_to_points(
        input_folder=input_path,
        output_folder=output_path,
        point_spacing=config.spacing  # 通过参数传递，而不是global
    )
    
    return output_path


def run_pipeline_step3_masks(config: PipelineConfig, input_path: str) -> str:
    """步骤3: 生成高斯掩码"""
    print("=" * 50)
    print("步骤3: 生成高斯掩码")
    print("=" * 50)
    
    # 确定输出路径
    output_path = os.path.join(config.output_folder, 'step3_masks')
    
    # 调用掩码生成函数，传递参数
    generate_masks(
        input_folder=input_path,
        output_folder=output_path,
        kernel_scale=config.kernel_scale,
        default_spacing=config.default_spacing
    )
    
    return output_path


def run_full_pipeline(config: PipelineConfig):
    """运行完整管道"""
    print(f"开始处理管道")
    print(f"输入文件夹: {config.input_folder}")
    print(f"输出文件夹: {config.output_folder}")
    print(f"配置: scale_factor={config.scale_factor}, spacing={config.spacing}, kernel_scale={config.kernel_scale}")
    
    try:
        # 创建输出目录
        os.makedirs(config.output_folder, exist_ok=True)
        
        # 步骤1: 缩放
        scaled_path = run_pipeline_step1_scale(config)
        
        # 步骤2: 转换为点阵  
        points_path = run_pipeline_step2_convert(config, scaled_path)
        
        # 步骤3: 生成掩码
        masks_path = run_pipeline_step3_masks(config, points_path)
        
        print("=" * 50)
        print("管道处理完成！")
        print(f"最终输出: {masks_path}")
        print("=" * 50)
        
    except Exception as e:
        print(f"管道处理失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='数据处理管道')
    parser.add_argument('--input', '-i', default='./input', help='输入文件夹')
    parser.add_argument('--output', '-o', default='./output', help='输出文件夹')
    parser.add_argument('--config', '-c', help='配置文件路径')
    
    # 可选的个别参数覆盖
    parser.add_argument('--scale', type=float, help='缩放比例（覆盖配置文件）')
    parser.add_argument('--spacing', type=float, help='点间距（覆盖配置文件）')
    parser.add_argument('--kernel-scale', type=float, help='核缩放（覆盖配置文件）')
    
    # 运行特定步骤
    parser.add_argument('--step', choices=['1', '2', '3', 'all'], default='all', 
                       help='运行特定步骤（1=缩放, 2=转点阵, 3=生成掩码, all=全部）')
    
    args = parser.parse_args()
    
    # 加载配置
    if args.config and os.path.exists(args.config):
        config = PipelineConfig.from_json(args.config)
        print(f"从配置文件加载: {args.config}")
    else:
        config = PipelineConfig()
        print("使用默认配置")
    
    # 更新路径
    config.input_folder = args.input
    config.output_folder = args.output
    
    # 命令行参数覆盖配置文件
    if args.scale is not None:
        config.scale_factor = args.scale
    if args.spacing is not None:
        config.spacing = args.spacing
    if args.kernel_scale is not None:
        config.kernel_scale = args.kernel_scale
    
    # 保存当前配置
    config_save_path = os.path.join(config.output_folder, 'pipeline_config.json')
    os.makedirs(config.output_folder, exist_ok=True)
    config.save_to_json(config_save_path)
    print(f"当前配置已保存到: {config_save_path}")
    
    # 运行指定步骤
    if args.step == 'all':
        run_full_pipeline(config)
    elif args.step == '1':
        run_pipeline_step1_scale(config)
    elif args.step == '2':
        scaled_path = os.path.join(config.output_folder, 'step1_scaled')
        run_pipeline_step2_convert(config, scaled_path)
    elif args.step == '3':
        points_path = os.path.join(config.output_folder, 'step2_points')  
        run_pipeline_step3_masks(config, points_path)


if __name__ == '__main__':
    main()