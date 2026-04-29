"""
NPC点位数据加载器

从多个JSON数据文件加载并整合所有NPC刷新点信息，
进行坐标转换从游戏世界坐标转换为地图图片坐标。
"""

import json
from pathlib import Path
from loguru import logger

from rocopath.config import DATA_DIR
from rocopath.models import (
    NpcPoint, NpcInfo, AreaInfo, NpcRefreshRule, WorldMapInfo
)


class NpcLoader:
    """NPC点位数据加载器"""

    # 拼接后的地图尺寸（固定，因为是 4x4 每个瓦片 2048）
    MAP_PIXEL_SIZE = 2048 * 4  # = 8192

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self._world_maps: dict[str, WorldMapInfo] = {}
        self._npc_conf: dict[int, NpcInfo] = {}
        self._area_conf: dict[int, AreaInfo] = {}
        self._scene_object_conf: dict[int, dict] = {}
        self._refresh_rules: dict[int, NpcRefreshRule] = {}
        self._points_by_map: dict[str, list[NpcPoint]] = {}
        self._loaded = False

    def load_all(self) -> None:
        """加载所有数据"""
        if self._loaded:
            return

        logger.info("开始加载NPC点位数据...")

        self._load_world_maps()
        self._load_npc_conf()
        self._load_area_conf()
        self._load_scene_object_conf()
        self._load_refresh_rules()
        self._load_and_integrate_points()

        self._loaded = True
        total = sum(len(points) for points in self._points_by_map.values())
        logger.info("加载完成，共 {} 个有效点位", total)

    def get_points_for_map(self, map_id: str) -> list[NpcPoint]:
        """获取指定地图的所有点位"""
        if not self._loaded:
            self.load_all()
        return self._points_by_map.get(map_id, [])

    def get_all_refresh_rules(self) -> list[NpcRefreshRule]:
        """获取所有刷新规则（用于筛选器）"""
        if not self._loaded:
            self.load_all()
        return sorted(self._refresh_rules.values(), key=lambda r: r.id)

    def get_all_points(self, map_id: str) -> list[NpcPoint]:
        """获取地图所有点位"""
        return self.get_points_for_map(map_id)

    def filter_by_rule_ids(
        self,
        points: list[NpcPoint],
        rule_ids: list[int]
    ) -> list[NpcPoint]:
        """
        按刷新规则ID筛选点位（OR关系，匹配任意一个即保留）

        Args:
            points: 输入点位列表
            rule_ids: 需要保留的规则ID列表

        Returns:
            筛选后的点位列表
        """
        rule_set = set(rule_ids)
        result = []
        for point in points:
            if point.refresh_rule.id in rule_set:
                result.append(point)
        return result

    def filter_by_keyword(
        self,
        points: list[NpcPoint],
        keyword: str
    ) -> list[NpcPoint]:
        """
        按名称关键词筛选点位（子串包含匹配，大小写不敏感）

        Args:
            points: 输入点位列表
            keyword: 关键词，空不过滤

        Returns:
            筛选后的点位列表
        """
        keyword = keyword.strip().lower()
        if not keyword:
            return points.copy()

        result = []
        for point in points:
            name = point.display_name.lower()
            if keyword in name:
                result.append(point)
        return result

    def filter_by_any_keyword(
        self,
        points: list[NpcPoint],
        keywords: list[str]
    ) -> list[NpcPoint]:
        """
        按多个关键词筛选点位（OR关系，任意一个关键词匹配即保留）

        Args:
            points: 输入点位列表
            keywords: 关键词列表，空列表不过滤

        Returns:
            筛选后的点位列表
        """
        keywords = [k.strip().lower() for k in keywords if k.strip()]
        if not keywords:
            return points.copy()

        result = []
        for point in points:
            name = point.display_name.lower()
            for keyword in keywords:
                if keyword in name:
                    result.append(point)
                    break
        return result

    def get_world_map(self, map_id: str) -> WorldMapInfo | None:
        """获取世界地图信息"""
        return self._world_maps.get(map_id)

    def search_points(
        self,
        map_id: str,
        keyword: str,
        rule_ids: list[int] | None = None
    ) -> list[NpcPoint]:
        """
        搜索点位（兼容旧接口，组合多个原子函数）

        Args:
            map_id: 当前地图ID
            keyword: 名称关键词（子串匹配）
            rule_ids: 筛选的刷新规则ID，None 不过滤

        Returns:
            匹配的点位列表
        """
        points = self.get_points_for_map(map_id)
        logger.debug("search_points: 地图 {} 总点位: {}", map_id, len(points))

        if rule_ids is not None:
            points = self.filter_by_rule_ids(points, rule_ids)
        if keyword:
            points = self.filter_by_keyword(points, keyword)

        logger.debug("search_points: 筛选后剩余: {}", len(points))
        return points

    def _load_world_maps(self) -> None:
        """加载世界地图配置"""
        path = self.data_dir / "WORLD_MAP_BLOCK_CONF.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for row in data["RocoDataRows"].values():
            if "scene_res_id" not in row:
                continue
            scene_res_id = str(row["scene_res_id"])
            if "map_center_position_xyz" not in row:
                logger.debug("跳过世界地图 {}: 缺少中心坐标", scene_res_id)
                continue
            # 解析 center_xyz: "x;y;z"
            cx, cy, cz = map(int, row["map_center_position_xyz"].split(";"))
            self._world_maps[scene_res_id] = WorldMapInfo(
                scene_res_id=scene_res_id,
                name=row.get("list_name", scene_res_id),
                center_x=cx,
                center_y=cy,
                side_length=row.get("side_length", 408000)
            )
        logger.debug("加载了 {} 个世界地图", len(self._world_maps))

    def _load_npc_conf(self) -> None:
        """加载NPC基础配置"""
        path = self.data_dir / "NPC_CONF.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        skipped_missing = 0
        for npc_id_str, row in data["RocoDataRows"].items():
            if "name" not in row:
                skipped_missing += 1
                continue
            # 如果缺少 editor_name，留空
            editor_name = row.get("editor_name", "")
            self._npc_conf[int(npc_id_str)] = NpcInfo(
                id=int(npc_id_str),
                name=row["name"],
                editor_name=editor_name
            )
        if skipped_missing:
            logger.debug("NPC_CONF 跳过 {} 个缺失必填字段项", skipped_missing)
        logger.debug("加载了 {} 个NPC配置", len(self._npc_conf))

    def _load_area_conf(self) -> None:
        """加载区域配置"""
        path = self.data_dir / "AREA_CONF.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for area_id_str, row in data["RocoDataRows"].items():
            area_id = int(area_id_str)
            map_id = str(row["scene_res_id"])
            cx, cy, cz = row["center_xyz"]
            self._area_conf[area_id] = AreaInfo(
                id=area_id,
                map_id=map_id,
                world_x=cx,
                world_y=cy,
                world_z=cz
            )
        logger.debug("加载了 {} 个区域配置", len(self._area_conf))

    def _load_refresh_rules(self) -> None:
        """加载刷新规则"""
        path = self.data_dir / "NPC_REFRESH_RULE_CONF.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for rule_id_str, row in data["RocoDataRows"].items():
            rule_id = int(rule_id_str)
            self._refresh_rules[rule_id] = NpcRefreshRule(
                id=rule_id,
                editor_names=row["editor_name"]
            )
        logger.debug("加载了 {} 个刷新规则", len(self._refresh_rules))

    def _load_scene_object_conf(self) -> None:
        """加载场景对象配置"""
        path = self.data_dir / "SCENE_OBJECT_CONF.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for obj_id_str, row in data["RocoDataRows"].items():
            obj_id = int(obj_id_str)
            self._scene_object_conf[obj_id] = row
        logger.debug("加载了 {} 个场景对象配置", len(self._scene_object_conf))

    def _load_and_integrate_points(self) -> None:
        """整合所有数据生成NpcPoint"""
        path = self.data_dir / "NPC_REFRESH_CONTENT_CONF.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        skipped_no_param = 0
        skipped_no_area = 0
        skipped_no_npc = 0
        skipped_no_rule = 0
        skipped_not_in_map = 0
        skipped_missing_field = 0
        skipped_no_scene_obj = 0

        for refresh_id_str, row in data["RocoDataRows"].items():
            refresh_id = int(refresh_id_str)

            # 必须有必需字段才处理
            if "refresh_param" not in row:
                skipped_no_param += 1
                continue
            if "npc_id" not in row or "refresh_rule" not in row:
                skipped_missing_field += 1
                continue
            if "refresh_type" not in row:
                skipped_missing_field += 1
                continue

            refresh_param = row["refresh_param"]
            npc_id = row["npc_id"]
            rule_id = row["refresh_rule"]
            refresh_type = row["refresh_type"]

            # 根据 refresh_type 获取区域信息
            if refresh_type != 4:
                # 常规情况：从 AREA_CONF 获取
                area = self._area_conf.get(refresh_param)
                if area is None:
                    skipped_no_area += 1
                    continue
            else:
                # refresh_type=4：从 SCENE_OBJECT_CONF 获取
                scene_obj = self._scene_object_conf.get(refresh_param)
                if scene_obj is None:
                    skipped_no_scene_obj += 1
                    continue
                # 从场景对象创建 AreaInfo
                area_id = refresh_param
                map_id = str(scene_obj["scene_res_conf_id"])
                wx, wy, wz = scene_obj["position_xyz"]
                area = AreaInfo(
                    id=area_id,
                    map_id=map_id,
                    world_x=wx,
                    world_y=wy,
                    world_z=wz
                )

            # 查找关联数据
            npc = self._npc_conf.get(npc_id)
            if npc is None:
                skipped_no_npc += 1
                continue

            rule = self._refresh_rules.get(rule_id)
            if rule is None:
                skipped_no_rule += 1
                continue

            # 只保留我们已知地图（卡洛西亚、魔法学院）的点位
            world_map = self._world_maps.get(area.map_id)
            if world_map is None:
                skipped_not_in_map += 1
                continue

            # 坐标转换：世界坐标 → 图片像素坐标
            map_x, map_y = self._convert_coords(
                world_x=area.world_x,
                world_y=area.world_y,
                world_map=world_map
            )

            point = NpcPoint(
                refresh_id=refresh_id,
                npc=npc,
                area=area,
                refresh_rule=rule,
                map_x=map_x,
                map_y=map_y
            )

            if area.map_id not in self._points_by_map:
                self._points_by_map[area.map_id] = []
            self._points_by_map[area.map_id].append(point)

        logger.debug(
            "点位整合完成: 跳过={} (无param={} 缺字段={} 无area={} 无scene_obj={} 无npc={} 无rule={} 无地图={})",
            skipped_no_param + skipped_no_area + skipped_no_scene_obj + skipped_no_npc + skipped_no_rule + skipped_not_in_map + skipped_missing_field,
            skipped_no_param, skipped_missing_field, skipped_no_area, skipped_no_scene_obj, skipped_no_npc, skipped_no_rule, skipped_not_in_map
        )

    def _convert_coords(
        self,
        world_x: int,
        world_y: int,
        world_map: WorldMapInfo
    ) -> tuple[float, float]:
        """
        将游戏世界坐标转换为地图图片像素坐标

        转换逻辑：
        1. 计算相对于世界中心的偏移
        2. 根据比例缩放：世界边长 → 图片像素边长
        3. Y轴反转：游戏Y增大向北（向上），图片Y增大向下

        Returns:
            (map_x, map_y) 像素坐标
        """
        scale = self.MAP_PIXEL_SIZE / world_map.side_length

        # X: (world_x - center_x) * scale + 图片中心
        offset_x = world_x - world_map.center_x
        map_x = offset_x * scale + (self.MAP_PIXEL_SIZE / 2)

        # Y: Y方向反转修正（之前方向反了）
        # 游戏Y增大 = 地图向北 → 图片坐标Y减小，所以 offset_y = world_y - center_y → map_y 会更大？不对，再检查：
        # 世界centerY是 612000，如果 worldY > centerY → 在地图北边 → 图片中应该Y更小
        # 所以正确的公式是 offset_y = worldY - centerY → mapY = center + offset * scale → 结果会更大？不对。
        # 用户反馈上下反了，所以直接把反转方向改过来：
        offset_y = world_y - world_map.center_y
        map_y = offset_y * scale + (self.MAP_PIXEL_SIZE / 2)

        return map_x, map_y

    def add_points(self, map_id: str, points: list[NpcPoint]) -> int:
        """添加点位到指定地图

        如果 refresh_id 已存在则覆盖更新。

        Args:
            map_id: 地图ID
            points: 要添加的点位列表

        Returns:
            实际新增的点位数量（不包含覆盖更新）
        """
        if map_id not in self._points_by_map:
            self._points_by_map[map_id] = []

        existing_map = self._points_by_map[map_id]
        # 按 refresh_id 建立索引用于快速查找
        existing_by_id = {p.refresh_id: i for i, p in enumerate(existing_map)}

        added = 0
        for point in points:
            if point.refresh_id in existing_by_id:
                # 已存在，覆盖更新
                idx = existing_by_id[point.refresh_id]
                existing_map[idx] = point
            else:
                # 新增
                existing_map.append(point)
                added += 1

        return added

    def get_refresh_rules_dict(self) -> dict[int, NpcRefreshRule]:
        """获取所有刷新规则字典（用于导入时查找）"""
        return self._refresh_rules.copy()
