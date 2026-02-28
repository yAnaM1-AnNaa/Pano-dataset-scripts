"""
Demonstrate polygon auto-fix behavior with buffer(0).
"""

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon
from shapely.validation import explain_validity


def visualize_fix(points, title_prefix=""):
    poly_original = Polygon(points)
    poly_fixed = poly_original.buffer(0)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    ax1 = axes[0]
    pts = np.array(points)
    closed_pts = np.vstack([pts, pts[0]])
    ax1.plot(closed_pts[:, 0], closed_pts[:, 1], "b-o", linewidth=2, markersize=8, label="Original boundary")
    for i, (x, y) in enumerate(points):
        ax1.annotate(f"P{i}", (x, y), xytext=(5, 5), textcoords="offset points", fontsize=10)
    ax1.set_title(f"{title_prefix}Original\nvalid: {poly_original.is_valid}\nreason: {explain_validity(poly_original)}")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.axis("equal")

    ax2 = axes[1]
    if poly_fixed.geom_type == "Polygon":
        x, y = poly_fixed.exterior.xy
        ax2.fill(x, y, alpha=0.3, color="green", label="Fixed area")
        ax2.plot(x, y, "g-o", linewidth=2, markersize=8, label="Fixed boundary")
    elif poly_fixed.geom_type == "MultiPolygon":
        for idx, geom in enumerate(poly_fixed.geoms):
            x, y = geom.exterior.xy
            ax2.fill(x, y, alpha=0.3, label=f"Part {idx + 1}")
            ax2.plot(x, y, "-o", linewidth=2, markersize=8)
    ax2.set_title(f"{title_prefix}Fixed\nvalid: {poly_fixed.is_valid}\ntype: {poly_fixed.geom_type}")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.axis("equal")
    plt.tight_layout()
    return fig, poly_original, poly_fixed


def demonstrate_buffer_zero():
    print("=" * 70)
    print("buffer(0) auto-fix demonstration")
    print("=" * 70)

    print("\n[Case 1: self-intersecting polygon]")
    points1 = [
        [1833.5905172413793, 483.18965517241384],
        [1834.6681034482758, 522.6293103448277],
        [1901.6939655172414, 524.7844827586207],
        [1901.0474137931035, 482.11206896551727],
        [1833.1594827586207, 485.7758620689655],
    ]
    poly1_orig = Polygon(points1)
    poly1_fixed = poly1_orig.buffer(0)
    print(f"Original: valid={poly1_orig.is_valid}, points={len(points1)}, area={poly1_orig.area:.2f}")
    print(f"Fixed: valid={poly1_fixed.is_valid}, points={len(poly1_fixed.exterior.coords)-1}, area={poly1_fixed.area:.2f}")
    print(f"Reason: {explain_validity(poly1_orig)}")

    print("\n[Case 2: figure-eight polygon]")
    points2 = [[0, 0], [2, 2], [2, 0], [0, 2]]
    poly2_orig = Polygon(points2)
    poly2_fixed = poly2_orig.buffer(0)
    print(f"Original: valid={poly2_orig.is_valid}")
    print(f"Fixed: valid={poly2_fixed.is_valid}, type={poly2_fixed.geom_type}")
    print(f"Reason: {explain_validity(poly2_orig)}")

    print("\n[Case 3: duplicated adjacent points]")
    points3 = [[0, 0], [10, 0], [10, 0], [10, 10], [0, 10]]
    poly3_orig = Polygon(points3)
    poly3_fixed = poly3_orig.buffer(0)
    print(f"Original: valid={poly3_orig.is_valid}")
    print(f"Fixed: valid={poly3_fixed.is_valid}")
    print(f"Reason: {explain_validity(poly3_orig)}")

    fig, _, _ = visualize_fix(points1, "Case 1: ")
    plt.savefig("/root/autodl-tmp/OOAL/polygon_fix_demo.png", dpi=150, bbox_inches="tight")
    print("\nVisualization saved to: /root/autodl-tmp/OOAL/polygon_fix_demo.png")


def compare_methods():
    print("\n" + "=" * 70)
    print("Method comparison")
    print("=" * 70)
    points = [
        [1833.5905172413793, 483.18965517241384],
        [1834.6681034482758, 522.6293103448277],
        [1901.6939655172414, 524.7844827586207],
        [1901.0474137931035, 482.11206896551727],
        [1833.1594827586207, 485.7758620689655],
    ]
    poly_orig = Polygon(points)
    methods = []
    try:
        methods.append(("buffer(0)", poly_orig.buffer(0)))
    except Exception as e:
        methods.append(("buffer(0)", f"failed: {e}"))
    try:
        from shapely import make_valid
        methods.append(("make_valid()", make_valid(poly_orig)))
    except Exception as e:
        methods.append(("make_valid()", f"failed: {e}"))
    try:
        methods.append(("simplify + buffer", poly_orig.simplify(0.1).buffer(0)))
    except Exception as e:
        methods.append(("simplify + buffer", f"failed: {e}"))

    print(f"\nOriginal polygon: valid={poly_orig.is_valid}, area={poly_orig.area:.2f}")
    print("\nMethod results:")
    for name, result in methods:
        if isinstance(result, str):
            print(f"  {name}: {result}")
        else:
            print(f"  {name}:")
            print(f"    - valid: {result.is_valid}")
            print(f"    - type: {result.geom_type}")
            print(f"    - area: {result.area:.2f}")
            print(f"    - area error: {abs(result.area - poly_orig.area)/poly_orig.area*100:.4f}%")


if __name__ == "__main__":
    demonstrate_buffer_zero()
    compare_methods()
