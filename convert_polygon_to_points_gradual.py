import json
import os
import argparse
from pathlib import Path
from shapely.geometry import Polygon, Point
import numpy as np

def calculate_distance_to_boundary(point, polygon):
    """计算点到多边形边界的距离"""
    return polygon.boundary.distance(Point(point))

def generate_adaptive_points(polygon, inner_spacing=1, outer_spacing=3, transition_ratio=0.3, edge_exclusion=5.0):
    """
    自适应生成点：内部密集，外部稀疏，边缘排除
    
    Args:
        polygon: Shapely Polygon对象
        inner_spacing: 内部区域点间距
        outer_spacing: 外部区域点间距
        transition_ratio: 过渡区域占比（0-1）
        edge_exclusion: 边缘排除距离（像素），距离边界小于此值的点不生成
    """
    bounds = polygon.bounds
    minx, miny, maxx, maxy = bounds
    
    # 第一遍：计算所有候选点及其到边界的距离
    candidate_points = []
    max_distance = 0
    
    for x in np.arange(minx, maxx, inner_spacing):
        for y in np.arange(miny, maxy, inner_spacing):
            p = Point(x, y)
            if polygon.contains(p):
                dist = calculate_distance_to_boundary((x, y), polygon)
                
                # 排除距离边界太近的点
                if dist < edge_exclusion:
                    continue
                
                max_distance = max(max_distance, dist)
                candidate_points.append((x, y, dist))
    
    if max_distance == 0:
        max_distance = 1
    
    # 定义过渡边界距离（从边界开始的过渡区域宽度）
    transition_threshold = max_distance * (1 - transition_ratio)
    
    points = []
    
    # 第二遍：根据距离决定是否保留该点
    for x, y, dist in candidate_points:
        if dist >= transition_threshold:
            # 内部核心区域：保留所有点（密集）
            points.append([x, y])
        else:
            # 过渡区域和边缘：根据距离计算跳过概率
            # dist接近0（边缘）→ ratio接近0 → 跳过概率高（稀疏）
            # dist接近threshold（靠近内部）→ ratio接近1 → 跳过概率低（密集）
            ratio = dist / transition_threshold
            
            # 计算当前位置应有的采样间距
            # ratio=0（边缘）→ spacing=outer_spacing（最稀疏）
            # ratio=1（接近内部）→ spacing=inner_spacing（最密集）
            current_spacing = outer_spacing - (outer_spacing - inner_spacing) * ratio
            
            # 使用网格对齐方式决定是否保留该点
            # 将坐标映射到对应间距的网格
            grid_x = round(x / current_spacing)
            grid_y = round(y / current_spacing)
            
            # 计算该网格点在原始inner_spacing下的对应位置
            expected_x = grid_x * current_spacing
            expected_y = grid_y * current_spacing
            
            # 如果当前点接近该网格点，则保留
            tolerance = inner_spacing * 0.6  # 容差
            if abs(x - expected_x) < tolerance and abs(y - expected_y) < tolerance:
                points.append([x, y])
    
    return points

def process_json_file(input_path, output_path, inner_spacing=1, outer_spacing=3, transition_ratio=0.3, edge_exclusion=5.0):
    """处理单个JSON文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    output_data = {
        "version": data.get("version", ""),
        "flags": data.get("flags", {}),
        "shapes": [],
        "imagePath": data.get("imagePath", ""),
        "imageData": data.get("imageData"),
        "imageHeight": data.get("imageHeight", 0),
        "imageWidth": data.get("imageWidth", 0),
        "original_polygons": []  # 保存原始多边形用于后续裁剪
    }
    
    for shape in data.get("shapes", []):
        if shape["shape_type"] == "polygon":
            polygon_points = shape["points"]
            polygon = Polygon(polygon_points)
            
            # 保存原始多边形
            output_data["original_polygons"].append(polygon_points)
            
            # 使用自适应点生成
            points = generate_adaptive_points(
                polygon, 
                inner_spacing=inner_spacing,
                outer_spacing=outer_spacing,
                transition_ratio=transition_ratio,
                edge_exclusion=edge_exclusion
            )
            
            new_shape = {
                "label": shape["label"],
                "points": points,
                "group_id": shape.get("group_id"),
                "description": shape.get("description", ""),
                "shape_type": "points",
                "flags": shape.get("flags", {})
            }
            output_data["shapes"].append(new_shape)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description='将多边形标注转换为自适应密度的点标注')
    parser.add_argument('-i', '--input', required=True, help='输入目录路径')
    parser.add_argument('-o', '--output', required=True, help='输出目录路径')
    parser.add_argument('-s', '--inner-spacing', type=float, default=1, help='内部点间距（默认1）')
    parser.add_argument('-os', '--outer-spacing', type=float, default=3, help='外部点间距（默认3）')
    parser.add_argument('-t', '--transition', type=float, default=0.3, help='过渡区域占比（0-1，默认0.3）')
    parser.add_argument('-e', '--edge-exclusion', type=float, default=5.0, help='边缘排除距离（像素，默认5.0）')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    json_files = list(input_dir.rglob("*.json"))
    
    for json_file in json_files:
        relative_path = json_file.relative_to(input_dir)
        output_path = output_dir / relative_path
        
        print(f"处理: {json_file}")
        process_json_file(
            json_file, 
            output_path, 
            args.inner_spacing,
            args.outer_spacing,
            args.transition,
            args.edge_exclusion
        )
    
    print(f"完成！共处理 {len(json_files)} 个文件")

if __name__ == "__main__":
    main()