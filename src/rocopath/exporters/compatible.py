"""
兼容第三方格式导出器

导出格式符合第三方导航工具要求的 JSON 格式。
坐标需要从当前地图像素坐标线性变换到兼容坐标系。

参考点对：
    兼容坐标    ↔    当前坐标
  (1569, 4092)  ↔  (2542, 5677)
  (5035, 2791)  ↔  (6008, 4376)
"""

import json
from dataclasses import dataclass


# 参考点对：(compatible_x, compatible_y, current_x, current_y)
REFERENCE_POINTS = [
    (1569, 4092, 2542, 5677),
    (5035, 2791, 6008, 4376),
]


def _calculate_linear_transformation() -> tuple[float, float]:
    """根据参考点计算线性变换系数

    变换公式：compatible = k * current + offset
    由于两个点给出的变换恰好是 k=1，只需要计算偏移量

    Returns:
        (offset_x, offset_y)
    """
    # 解方程组：
    # c1 = k * n1 + o
    # c2 = k * n2 + o
    # => (c1 - c2) = k * (n1 - n2)
    # => k = (c1 - c2) / (n1 - n2)
    # => o = c1 - k * n1

    c1_x, c1_y, n1_x, n1_y = REFERENCE_POINTS[0]
    c2_x, c2_y, n2_x, n2_y = REFERENCE_POINTS[1]

    k_x = (c1_x - c2_x) / (n1_x - n2_x)
    k_y = (c1_y - c2_y) / (n1_y - n2_y)

    offset_x = c1_x - k_x * n1_x
    offset_y = c1_y - k_y * n1_y

    return offset_x, offset_y


# 预计算偏移量
OFFSET_X, OFFSET_Y = _calculate_linear_transformation()


@dataclass
class CompatiblePoint:
    """单个兼容路径点"""
    x: int
    y: int
    label: str
    radius: int = 30


def transform_coordinate(original_x: float, original_y: float) -> tuple[int, int]:
    """将当前地图坐标变换为兼容坐标

    Args:
        original_x: 当前地图坐标 x
        original_y: 当前地图坐标 y

    Returns:
        (compatible_x, compatible_y) 变换后的整数坐标
    """
    compatible_x = int(round(original_x + OFFSET_X))
    compatible_y = int(round(original_y + OFFSET_Y))
    return compatible_x, compatible_y


def parse_compatible_json(json_str: str) -> tuple[str, bool, str, list[tuple[float, float, str]]]:
    """解析旧版兼容格式 JSON，逆变换坐标

    Args:
        json_str: JSON 字符串

    Returns:
        (name, loop, notes, [(original_x, original_y, label), ...])
    """
    data = json.loads(json_str)
    name = data.get("name", "")
    loop = data.get("loop", False)
    notes = data.get("notes", "")
    points = []
    for p in data.get("points", []):
        # 逆变换：original = compatible - offset
        orig_x = p["x"] - OFFSET_X
        orig_y = p["y"] - OFFSET_Y
        label = p.get("label", "")
        points.append((orig_x, orig_y, label))
    return name, loop, notes, points


def generate_compatible_json(
    name: str,
    notes: str,
    points: list[tuple[float, float]],
    loop: bool = False
) -> str:
    """生成兼容格式的 JSON 字符串

    Args:
        name: 路径名称
        notes: 路径说明备注
        points: 路径点坐标列表 [(x, y), ...]，起点到终点顺序
        loop: 是否循环，默认为 False

    Returns:
        JSON 字符串，中文以 Unicode 转义输出（符合第三方格式要求）
    """
    compatible_points = []
    for i, (x, y) in enumerate(points, 1):
        cx, cy = transform_coordinate(x, y)
        compatible_points.append({
            "x": cx,
            "y": cy,
            "label": f"节点 {i}",
            "radius": 30
        })

    data = {
        "name": name,
        "loop": loop,
        "notes": notes,
        "points": compatible_points
    }

    # ensure_ascii=True → 中文以 Unicode 转义输出，符合第三方格式要求
    json_str = json.dumps(data, indent=2, ensure_ascii=True)
    return json_str
