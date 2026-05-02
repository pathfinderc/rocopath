import json

def parse_new_compatible_json(json_str: str) -> tuple[str, bool, str, list[tuple[float, float, str]]]:
    """解析新版兼容格式 JSON，坐标保持原样

    Args:
        json_str: JSON 字符串

    Returns:
        (name, loop, notes, [(x, y, label), ...])
    """
    data = json.loads(json_str)
    name = data.get("name", "")
    loop = data.get("loop", False)
    notes = data.get("notes", "")
    points = [(p["x"], p["y"], p.get("label", "")) for p in data.get("points", [])]
    return name, loop, notes, points


def generate_new_compatible_json(
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
        cx, cy = (x, y)
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
