"""
NPC点位导入导出器

导出/导入当前地图所有NPC点位的完整信息，包括：
- 世界坐标 (world_x, world_y, world_z)
- 世界边长 (side_length)
- 像素坐标 (map_x, map_y)
- name (NPC名称)
- editorname (编辑器名称)
- npc_id (NPC ID)

同时支持导出已规划路径：
- 每条路径包含完整的点位信息列表
- 保留路径顺序和总距离信息
"""

import json
from datetime import datetime
from typing import List, Tuple

from rocopath.models import (
    NpcPoint, NpcInfo, AreaInfo, NpcRefreshRule, WorldMapInfo
)
from rocopath.ui.map_scene import PlannedRoute


def generate_npc_export_json(
    map_id: str,
    map_name: str,
    world_map: WorldMapInfo,
    npc_points: List[NpcPoint]
) -> str:
    """
    生成NPC点位导出JSON字符串

    Args:
        map_id: 地图ID
        map_name: 地图名称
        world_map: 世界地图信息（包含side_length等）
        npc_points: NPC点位列表

    Returns:
        JSON字符串，使用UTF-8编码，中文不转义
    """
    # 构建点位列表
    points_data = []
    for point in npc_points:
        point_data = {
            "refresh_id": point.refresh_id,
            "npc_id": point.npc.id,
            "name": point.npc.name,
            "editorname": point.npc.editor_name,
            "world_x": point.area.world_x if point.area else 0,
            "world_y": point.area.world_y if point.area else 0,
            "world_z": point.area.world_z if point.area else 0,
            "map_x": point.map_x,
            "map_y": point.map_y,
            "refresh_rule_id": point.refresh_rule.id
        }
        points_data.append(point_data)

    # 构建完整数据结构
    data = {
        "version": "1.0",
        "export_time": datetime.now().isoformat(),
        "map_info": {
            "map_id": map_id,
            "map_name": map_name,
            "side_length": world_map.side_length,
            "center_x": world_map.center_x,
            "center_y": world_map.center_y
        },
        "total_points": len(points_data),
        "npc_points": points_data
    }

    # 生成JSON字符串
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    return json_str


def parse_npc_import_json(
    json_content: str
) -> Tuple[dict, List[dict]]:
    """
    解析导入的JSON文件

    Args:
        json_content: JSON文件内容字符串

    Returns:
        (map_info_dict, points_data_list)
        map_info_dict 包含 map_id, map_name, side_length, center_x, center_y
        points_data_list 是所有点位数据的列表

    Raises:
        ValueError: 当JSON格式不正确或缺少必要字段时抛出
    """
    data = json.loads(json_content)

    # 验证版本
    version = data.get("version")
    if version not in ("1.0", "1"):
        raise ValueError(f"不支持的导出格式版本: {version}，当前仅支持 1.0")

    # 验证地图信息
    map_info = data.get("map_info", {})
    required_map_fields = ["map_id", "map_name"]
    for field in required_map_fields:
        if field not in map_info:
            raise ValueError(f"地图信息缺少必要字段: {field}")

    # 获取点位列表
    points_data = data.get("npc_points", [])
    if not isinstance(points_data, list):
        raise ValueError("npc_points 不是有效的数组")

    # 验证每个点位包含必要字段
    required_point_fields = [
        "refresh_id", "npc_id", "name", "editorname",
        "world_x", "world_y", "world_z", "map_x", "map_y",
        "refresh_rule_id"
    ]
    for i, point in enumerate(points_data):
        if not isinstance(point, dict):
            raise ValueError(f"第 {i+1} 个点位不是有效的对象")
        for field in required_point_fields:
            if field not in point:
                raise ValueError(f"第 {i+1} 个点位缺少必要字段: {field}")

    return map_info, points_data


def rebuild_npc_points(
    points_data: List[dict],
    current_map_id: str,
    refresh_rules: dict[int, NpcRefreshRule]
) -> List[NpcPoint]:
    """
    从导入的点位数据重建 NpcPoint 对象列表

    Args:
        points_data: 解析后的点位数据列表
        current_map_id: 当前加载的地图ID，所有导入点位都会归属到这里
        refresh_rules: 现有的刷新规则字典 {rule_id: NpcRefreshRule}

    Returns:
        重建后的 NpcPoint 列表
    """
    result: List[NpcPoint] = []

    for data in points_data:
        # 重建 NPC 信息
        npc_info = NpcInfo(
            id=int(data["npc_id"]),
            name=data["name"],
            editor_name=data["editorname"]
        )

        # 重建 区域信息
        area_info = AreaInfo(
            id=int(data.get("refresh_id", 0)),
            map_id=current_map_id,
            world_x=int(data["world_x"]),
            world_y=int(data["world_y"]),
            world_z=int(data["world_z"])
        )

        # 获取刷新规则（如果找不到使用默认占位）
        rule_id = int(data["refresh_rule_id"])
        refresh_rule = refresh_rules.get(rule_id)
        if refresh_rule is None:
            # 如果找不到对应规则，创建一个最小规则
            refresh_rule = NpcRefreshRule(
                id=rule_id,
                editor_names=[f"unknown_{rule_id}"]
            )

        # 重建 NpcPoint
        npc_point = NpcPoint(
            refresh_id=int(data["refresh_id"]),
            npc=npc_info,
            area=area_info,
            refresh_rule=refresh_rule,
            map_x=float(data["map_x"]),
            map_y=float(data["map_y"])
        )
        result.append(npc_point)

    return result


def generate_route_export_json(
    map_id: str,
    map_name: str,
    world_map: WorldMapInfo,
    routes: List[PlannedRoute]
) -> str:
    """
    生成已规划路径导出JSON字符串

    Args:
        map_id: 地图ID
        map_name: 地图名称
        world_map: 世界地图信息（包含side_length等）
        routes: 已规划路径列表

    Returns:
        JSON字符串，使用UTF-8编码，中文不转义
    """
    # 构建路径列表
    routes_data = []
    for route_idx, route in enumerate(routes, 1):
        # 构建路径中每个点位的数据
        points_data = []
        for point in route.points:
            point_data = {
                "refresh_id": point.refresh_id,
                "npc_id": point.npc.id,
                "name": point.npc.name,
                "editorname": point.npc.editor_name,
                "world_x": point.area.world_x if point.area else 0,
                "world_y": point.area.world_y if point.area else 0,
                "world_z": point.area.world_z if point.area else 0,
                "map_x": point.map_x,
                "map_y": point.map_y,
                "refresh_rule_id": point.refresh_rule.id
            }
            points_data.append(point_data)

        # 添加路径数据
        route_data = {
            "route_index": route_idx,
            "total_distance": route.total_distance,
            "point_count": len(points_data),
            "points": points_data
        }
        routes_data.append(route_data)

    # 构建完整数据结构
    data = {
        "version": "1.0",
        "export_time": datetime.now().isoformat(),
        "map_info": {
            "map_id": map_id,
            "map_name": map_name,
            "side_length": world_map.side_length,
            "center_x": world_map.center_x,
            "center_y": world_map.center_y
        },
        "total_routes": len(routes_data),
        "routes": routes_data
    }

    # 生成JSON字符串
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    return json_str
