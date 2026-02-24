import numpy as np
import argparse
import json
import os
from shapely.geometry import Polygon

def scale_polygon(points:list, scale_factor:float):
    """
    等比例缩放多边形，保持中心点不变。（这里的是指质心）
    参数:
        points:[[x1, y1], [x2, y2], ...] 多边形顶点列表
        scale_factor: 缩放比例
    返回:
        list: 缩放后的顶点列表
    """
    # 注意：试图通过方程求解一个距离所有顶点等距的中心点（外心）对于不规则多边形通常是无解的。
    # 缩放多边形的标准做法是使用所有顶点的算术平均值（质心）作为中心。
    pts = np.array(points)
    
    # 1. 计算算术中心点 (Centroid)
    center = np.mean(pts, axis=0)
    # 2. 应用缩放公式: P' = Center + scale_factor * (P - Center)
    scaled_pts = center + scale_factor * (pts - center)
    return scaled_pts.tolist()
    
def shrink_polygon(points, distance, auto_fix=True):
    """
    收缩多边形
    参数:
        points: 多边形顶点列表
        distance: 收缩距离
        auto_fix: 是否自动修复无效多边形
    """
    poly = Polygon(points)
    if not poly.is_valid:
        return points, len(points)

    # poly.buffer执行收缩
    shrunk_poly = poly.buffer(-distance, join_style=2)
    # buffer操作可能返回 MultiPolygon（多边形分裂）或空几何
    if shrunk_poly.is_empty:
        # 收缩过度导致多边形消失
        return points, 0
    if shrunk_poly.geom_type == 'MultiPolygon':
        # 如果分裂成多个部分，取面积最大的
        shrunk_poly = max(shrunk_poly.geoms, key=lambda p: p.area)
    if shrunk_poly.geom_type != 'Polygon':
        # 其他不支持的几何类型
        return points, 0
   
    # shapely 返回的坐标通常最后一点和第一点重复，但是json不需要重复的点，所以需要去掉最后一点
    # xy都是只包含坐标的列表，需要结合到一起，得到坐标对。x只含有xi，y只含有yi
    x, y = shrunk_poly.exterior.xy
    coords = []
    for i in range(len(x)):
        coords.append([x[i], y[i]])
    new_points = coords[:-1]
    shrunk_len = len(new_points)
    
    return new_points, shrunk_len

def process_json_file(input_path, output_path, initial_distance, distance_dict):
    """
    处理单个JSON文件
    # JSON:{'version':'', 
    #       'shapes':[{'label':'', 'points':[[x1, y1], [x2, y2]]},
    #                 {'label':'', 'points':[[x1, y1], [x2, y2]]}]}
    """
    json_name = os.path.basename(input_path)
    try:
        distance_dict[json_name] = []
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for i in range(len(data['shapes'])):
            points = data['shapes'][i]['points'] 
            res_len = len(points)
            
            # 检查点数是否足够
            if res_len < 3:
                print(f"  警告: Shape {i} 的点数 {res_len} < 3, 无法形成有效多边形，跳过")
                continue
            
            # 修复无效多边形
            poly = Polygon(points)
            if not poly.is_valid:
                print(f"  Fixing shape {i}.")
                poly = poly.buffer(0)
                if poly.geom_type == 'MultiPolygon':
                    # 如果修复后是MultiPolygon，选择面积最大的部分作为新的多边形
                    poly = max(poly.geoms, key=lambda p: p.area)
                if poly.is_valid and poly.geom_type == 'Polygon':
                    # 更新points为修复后的坐标
                    x, y = poly.exterior.xy
                    points = [[x[j], y[j]] for j in range(len(x)-1)]
                else:
                    print(f"  Shape {i}: 修复失败，保持原始坐标")
            
            # 收缩：基于面积比
            original_area = Polygon(points).area
            current_distance = initial_distance
            
            for _ in range(50):  # 最多50次迭代
                new_points, shrunk_len = shrink_polygon(points, current_distance, auto_fix=False)
                if shrunk_len == 0 or current_distance < 0.5:
                    current_distance *= 0.95
                    continue
                shrunk_area = Polygon(new_points).area if shrunk_len > 2 else 0
                if shrunk_area >= original_area * 0.5:  # 达到原始面积的一定比例后停止
                    break
                current_distance *= 0.95
            
            data['shapes'][i]['points'] = new_points if shrunk_len > 0 else points
            distance_dict[json_name].append(current_distance)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False) 
        return True
    
    except Exception as e:
        print(f"✗ 处理 {input_path} 时出错: {str(e)}")
        return False

def process_directory_recursive(input_dir, output_dir, distance, config_path):
    """
    递归处理目录中的所有JSON文件，保持目录结构
    RGB  ./data/dataset6/Seen/testset/egocentric/bathe/bathtub/bathtub83.jpg
    GT   ./data/dataset6/Seen/testset/GT/bathe/bathtub/bathtub83.png
    JSON ./data/source/armset/armset1.json
    """
    success_count = 0
    error_count = 0
    all_distance_configs = {}  # 用于存储所有文件的配置
    
    # 使用os.walk递归遍历所有子目录
    for root, _, files in os.walk(input_dir):
        # 处理当前目录下的JSON文件
        for file in files:
            if file.endswith('.json'):
                input_file_path = os.path.join(root, file)
                output_file_path = os.path.join(output_dir, file)
                print(f"Processing {input_file_path}")
                if process_json_file(input_file_path, output_file_path, distance, all_distance_configs):
                    print(f"{file} Finished")
                    success_count += 1
                else:
                    error_count += 1
    
    # 所有文件处理完成后，一次性写入配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(all_distance_configs, f, indent=2, ensure_ascii=False)
    print(f"所有距离配置已保存至: {config_path}")
    
    return success_count, error_count

def main():
    parser = argparse.ArgumentParser(description='递归缩小文件夹中所有JSON文件的多边形')
    parser.add_argument('--input', '-i', default='/root/autodl-tmp/OOAL/data/temps/6/111', help='输入文件夹路径，递归处理所有子文件夹中的JSON文件')
    parser.add_argument('--output', '-o', default='/root/autodl-tmp/OOAL/data/temps/6/111result', help='输出文件夹路径，保持原有目录结构')
    parser.add_argument('--distance', '-d', type=float, default=50, help='缩放距离')
    parser.add_argument('--config', '-c', default='/root/autodl-tmp/OOAL/data/temps/6/shrink_config.json', help='保存每个文件缩放距离的配置文件路径')
    args = parser.parse_args()

    # 创建输出文件夹
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Output folder does not exist. Created output folder: {args.output}")
    
    print(f"Start processing  {args.input}")
    print(f"Shrink distance: {args.distance}")
    print(f"Output to: {args.output}")
    
    # 递归处理所有JSON文件
    success_count, error_count = process_directory_recursive(args.input, args.output, args.distance, args.config)
    
    print("-" * 50)
    print(f"Succededd {success_count}, Failed {error_count}")

if __name__ == '__main__':
    main()