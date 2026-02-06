"""
演示多边形自动修复的原理和效果
"""
from shapely.geometry import Polygon
from shapely.validation import explain_validity
import matplotlib.pyplot as plt
import numpy as np

def visualize_fix(points, title_prefix=""):
    """可视化修复前后的多边形"""
    # 原始多边形
    poly_original = Polygon(points)
    
    # 修复后的多边形
    poly_fixed = poly_original.buffer(0)
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # 左图：原始多边形
    ax1 = axes[0]
    pts = np.array(points)
    closed_pts = np.vstack([pts, pts[0]])
    ax1.plot(closed_pts[:, 0], closed_pts[:, 1], 'b-o', linewidth=2, markersize=8, label='原始边界')
    
    # 标注点
    for i, (x, y) in enumerate(points):
        ax1.annotate(f'P{i}', (x, y), xytext=(5, 5), textcoords='offset points', 
                    fontsize=10, bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    ax1.set_title(f'{title_prefix}原始多边形\n有效性: {poly_original.is_valid}\n原因: {explain_validity(poly_original)}')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.axis('equal')
    
    # 右图：修复后的多边形
    ax2 = axes[1]
    if poly_fixed.geom_type == 'Polygon':
        x, y = poly_fixed.exterior.xy
        ax2.fill(x, y, alpha=0.3, color='green', label='修复后区域')
        ax2.plot(x, y, 'g-o', linewidth=2, markersize=8, label='修复后边界')
        
        # 标注修复后的点
        for i in range(len(x)-1):
            ax2.annotate(f'F{i}', (x[i], y[i]), xytext=(5, 5), textcoords='offset points',
                        fontsize=10, bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7))
    elif poly_fixed.geom_type == 'MultiPolygon':
        for idx, geom in enumerate(poly_fixed.geoms):
            x, y = geom.exterior.xy
            ax2.fill(x, y, alpha=0.3, label=f'部分{idx+1}')
            ax2.plot(x, y, '-o', linewidth=2, markersize=8)
    
    ax2.set_title(f'{title_prefix}修复后多边形\n有效性: {poly_fixed.is_valid}\n类型: {poly_fixed.geom_type}')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.axis('equal')
    
    plt.tight_layout()
    return fig, poly_original, poly_fixed

def demonstrate_buffer_zero():
    """演示buffer(0)的修复原理"""
    print("=" * 70)
    print("buffer(0) 自动修复原理演示")
    print("=" * 70)
    
    # 示例1：自相交的多边形（您的案例）
    print("\n【案例1：自相交多边形】")
    points1 = [
        [1833.5905172413793, 483.18965517241384],
        [1834.6681034482758, 522.6293103448277],
        [1901.6939655172414, 524.7844827586207],
        [1901.0474137931035, 482.11206896551727],
        [1833.1594827586207, 485.7758620689655]
    ]
    
    poly1_orig = Polygon(points1)
    poly1_fixed = poly1_orig.buffer(0)
    
    print(f"原始: 有效={poly1_orig.is_valid}, 点数={len(points1)}, 面积={poly1_orig.area:.2f}")
    print(f"修复: 有效={poly1_fixed.is_valid}, 点数={len(poly1_fixed.exterior.coords)-1}, 面积={poly1_fixed.area:.2f}")
    print(f"解释: {explain_validity(poly1_orig)}")
    print(f"修复方式: buffer(0)在自相交点处分割并重建多边形")
    
    # 示例2：8字形多边形
    print("\n【案例2：8字形多边形】")
    points2 = [
        [0, 0], [2, 2], [2, 0], [0, 2]  # 形成8字
    ]
    poly2_orig = Polygon(points2)
    poly2_fixed = poly2_orig.buffer(0)
    
    print(f"原始: 有效={poly2_orig.is_valid}")
    print(f"修复: 有效={poly2_fixed.is_valid}, 类型={poly2_fixed.geom_type}")
    print(f"解释: {explain_validity(poly2_orig)}")
    print(f"修复方式: 将8字分割成两个独立的三角形")
    
    # 示例3：重复点
    print("\n【案例3：重复相邻点】")
    points3 = [
        [0, 0], [10, 0], [10, 0], [10, 10], [0, 10]  # P1和P2重复
    ]
    poly3_orig = Polygon(points3)
    poly3_fixed = poly3_orig.buffer(0)
    
    print(f"原始: 有效={poly3_orig.is_valid}")
    print(f"修复: 有效={poly3_fixed.is_valid}")
    print(f"解释: {explain_validity(poly3_orig)}")
    print(f"修复方式: 移除重复点，保留有效的边界")
    
    print("\n" + "=" * 70)
    print("buffer(0) 工作流程")
    print("=" * 70)
    print("""
    1. 输入：无效的多边形对象
    2. GEOS库处理：
       a. 解析多边形的所有边和顶点
       b. 检测交叉、重叠、重复等问题
       c. 应用拓扑规则重建有效几何
       d. 可能的操作：
          - 在交点处分割
          - 移除退化的边
          - 合并共线的边
          - 删除重复点
    3. 输出：有效的Polygon、MultiPolygon或GeometryCollection
    
    优点：
    ✓ 简单易用，一行代码解决
    ✓ 保持几何形状基本不变
    ✓ 面积变化通常很小（<1%）
    
    注意事项：
    ⚠ 可能改变几何类型（Polygon → MultiPolygon）
    ⚠ 需要处理返回类型的变化
    ⚠ 极少数情况下可能返回空几何
    """)
    
    # 可视化第一个案例
    fig, _, _ = visualize_fix(points1, "案例1: ")
    plt.savefig('/root/autodl-tmp/OOAL/polygon_fix_demo.png', dpi=150, bbox_inches='tight')
    print("\n可视化图已保存到: /root/autodl-tmp/OOAL/polygon_fix_demo.png")

def compare_methods():
    """比较不同的修复方法"""
    print("\n" + "=" * 70)
    print("修复方法对比")
    print("=" * 70)
    
    points = [
        [1833.5905172413793, 483.18965517241384],
        [1834.6681034482758, 522.6293103448277],
        [1901.6939655172414, 524.7844827586207],
        [1901.0474137931035, 482.11206896551727],
        [1833.1594827586207, 485.7758620689655]
    ]
    
    poly_orig = Polygon(points)
    
    methods = []
    
    # 方法1: buffer(0)
    try:
        poly_buffer = poly_orig.buffer(0)
        methods.append(('buffer(0)', poly_buffer))
    except Exception as e:
        methods.append(('buffer(0)', f"失败: {e}"))
    
    # 方法2: make_valid (Shapely 1.8+)
    try:
        from shapely import make_valid
        poly_make_valid = make_valid(poly_orig)
        methods.append(('make_valid()', poly_make_valid))
    except Exception as e:
        methods.append(('make_valid()', f"失败: {e}"))
    
    # 方法3: simplify + buffer(0)
    try:
        poly_simplify = poly_orig.simplify(0.1).buffer(0)
        methods.append(('simplify + buffer', poly_simplify))
    except Exception as e:
        methods.append(('simplify + buffer', f"失败: {e}"))
    
    print(f"\n原始多边形: 有效={poly_orig.is_valid}, 面积={poly_orig.area:.2f}")
    print("\n各方法结果:")
    for name, result in methods:
        if isinstance(result, str):
            print(f"  {name}: {result}")
        else:
            print(f"  {name}:")
            print(f"    - 有效: {result.is_valid}")
            print(f"    - 类型: {result.geom_type}")
            print(f"    - 面积: {result.area:.2f}")
            print(f"    - 面积误差: {abs(result.area - poly_orig.area)/poly_orig.area*100:.4f}%")

if __name__ == '__main__':
    demonstrate_buffer_zero()
    compare_methods()
