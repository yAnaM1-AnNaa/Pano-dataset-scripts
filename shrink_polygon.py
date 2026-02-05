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
    
def shrink_polygon(points, distance):
    poly = Polygon(points)
    if not poly.is_valid:
        return points # 或者尝试 poly.buffer(0) 修复
    
    # 执行收缩
    shrunk_poly = poly.buffer(-distance, join_style=2)
   
    # shapely 返回的坐标通常最后一点和第一点重复，但是json不需要重复的点，所以需要去掉最后一点
    x, y = shrunk_poly.exterior.xy
    new_points = list(zip(x, y))[:-1]
    
    return new_points

def process_json_file(input_path, output_path, scale_factor):
    """
    处理单个JSON文件
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for i in range(len(data['shapes'])):
            points = data['shapes'][i]['points']
            data['shapes'][i]['points'] = shrink_polygon(points, scale_factor)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False) 
        return True
    
    except Exception as e:
        print(f"✗ 处理 {input_path} 时出错: {str(e)}")
        return False

def process_directory_recursive(input_dir, output_dir, scale_factor):
    """
    递归处理目录中的所有JSON文件，保持目录结构
    RGB  ./data/dataset6/Seen/testset/egocentric/bathe/bathtub/bathtub83.jpg
    GT   ./data/dataset6/Seen/testset/GT/bathe/bathtub/bathtub83.png
    JSON ./data/source/armset/armset1.json
    """
    success_count = 0
    error_count = 0
    
    # 使用os.walk递归遍历所有子目录
    for root, _, files in os.walk(input_dir):
        # 处理当前目录下的JSON文件
        for file in files:
            if file.endswith('.json'):
                input_file_path = os.path.join(root, file)
                output_file_path = os.path.join(output_dir, file)
                print(f"Processing {input_file_path}")
                if process_json_file(input_file_path, output_file_path, scale_factor):
                    print(f"{file} Finished")
                    success_count += 1
                else:
                    error_count += 1
    
    return success_count, error_count

def main():
    parser = argparse.ArgumentParser(description='递归缩小文件夹中所有JSON文件的多边形')
    parser.add_argument('--input', '-i', default='./data/source', help='输入文件夹路径，递归处理所有子文件夹中的JSON文件')
    parser.add_argument('--output', '-o', default='./data/temps', help='输出文件夹路径，保持原有目录结构')
    parser.add_argument('--distance', '-d', type=float, default=0.4, help='缩放距离')
    args = parser.parse_args()

    # 创建输出文件夹
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Output folder does not exist. Created output folder: {args.output}")
    
    print(f"Start processing  {args.input}")
    print(f"Shrink distance: {args.distance}")
    print(f"Output to: {args.output}")
    
    # 递归处理所有JSON文件
    success_count, error_count = process_directory_recursive(args.input, args.output, args.distance)
    
    print("-" * 50)
    print(f"Succededd {success_count}, Failed {error_count}")

if __name__ == '__main__':
    main()