"""
地图控制器

作为 UI 和地图数据处理之间的中间层：
- 缓存已加载的地图
- 提供统一的地图加载接口
- 管理NPC点位，提供搜索筛选功能
"""

from rocopath.models import MapInfo, NpcPoint, NpcRefreshRule, WorldMapInfo
from rocopath.core.npc_loader import NpcLoader
from rocopath.utils.map import get_map
from rocopath.config import BIGWORLD_MAP_ID, BIGWORLD_NAME, MAGIC_ACADEMY_MAP_ID, MAGIC_ACADEMY_NAME


class MapController:
    """地图业务控制器"""

    def __init__(self):
        self._cache: dict[str, MapInfo] = {}
        # 预定义已知地图
        self._available_maps: dict[str, str] = {
            BIGWORLD_MAP_ID: BIGWORLD_NAME,
            MAGIC_ACADEMY_MAP_ID: MAGIC_ACADEMY_NAME,
        }
        # NPC点位加载器
        self._npc_loader = NpcLoader()
        # 懒加载
        self._npc_loaded = False

    def load_map(self, map_id: str) -> MapInfo | None:
        """
        加载指定地图

        优先从缓存获取，缓存未命中则从文件加载。

        Args:
            map_id: 地图ID

        Returns:
            加载成功返回 MapInfo，失败返回 None
        """
        # 检查缓存
        if map_id in self._cache:
            return self._cache[map_id]

        # 从文件加载
        image = get_map(map_id)
        if image is None:
            return None

        # 创建 MapInfo
        map_name = self._available_maps.get(map_id, map_id)
        map_info = MapInfo(
            map_id=map_id,
            name=map_name,
            width=image.width,
            height=image.height,
            image=image
        )

        # 缓存并返回
        self._cache[map_id] = map_info
        return map_info

    def get_available_maps(self) -> dict[str, str]:
        """获取所有可用地图列表 {map_id: name}"""
        return self._available_maps.copy()

    def add_available_map(self, map_id: str, name: str) -> None:
        """添加可用地图（后续动态加载可用）"""
        self._available_maps[map_id] = name
        # 如果已经缓存，更新名称
        if map_id in self._cache:
            self._cache[map_id].name = name

    def clear_cache(self) -> None:
        """清除地图缓存"""
        self._cache.clear()

    # === NPC点位相关 ===

    def get_all_refresh_rules(self) -> list[NpcRefreshRule]:
        """获取所有刷新规则（用于生成筛选复选框）"""
        self._ensure_npc_loaded()
        return self._npc_loader.get_all_refresh_rules()

    def get_all_points(self, map_id: str) -> list[NpcPoint]:
        """获取地图所有点位"""
        self._ensure_npc_loaded()
        return self._npc_loader.get_all_points(map_id)

    def filter_by_rule_ids(
        self,
        points: list[NpcPoint],
        rule_ids: list[int]
    ) -> list[NpcPoint]:
        """按刷新规则ID筛选点位（OR关系）"""
        self._ensure_npc_loaded()
        return self._npc_loader.filter_by_rule_ids(points, rule_ids)

    def filter_by_keyword(
        self,
        points: list[NpcPoint],
        keyword: str
    ) -> list[NpcPoint]:
        """按名称关键词筛选点位（子串包含匹配）"""
        self._ensure_npc_loaded()
        return self._npc_loader.filter_by_keyword(points, keyword)

    def filter_by_any_keyword(
        self,
        points: list[NpcPoint],
        keywords: list[str]
    ) -> list[NpcPoint]:
        """按多个关键词筛选点位（任意匹配，OR关系）"""
        self._ensure_npc_loaded()
        return self._npc_loader.filter_by_any_keyword(points, keywords)

    def search_npc_points(
        self,
        map_id: str,
        keyword: str = "",
        rule_ids: list[int] | None = None
    ) -> list[NpcPoint]:
        """
        搜索NPC点位（兼容旧接口）

        Args:
            map_id: 当前地图ID
            keyword: 名称关键词搜索（子串匹配），空不过滤
            rule_ids: 筛选的刷新规则ID，None 不过滤

        Returns:
            匹配的点位列表
        """
        self._ensure_npc_loaded()
        return self._npc_loader.search_points(map_id, keyword, rule_ids)

    def get_point_by_refresh_id(self, map_id: str, refresh_id: int) -> NpcPoint | None:
        """根据refresh_id获取点位（用于点击查找）"""
        self._ensure_npc_loaded()
        points = self._npc_loader.get_points_for_map(map_id)
        for point in points:
            if point.refresh_id == refresh_id:
                return point
        return None

    def _ensure_npc_loaded(self) -> None:
        """确保NPC数据已加载"""
        if not self._npc_loaded:
            self._npc_loader.load_all()
            self._npc_loaded = True

    def get_world_map(self, map_id: str) -> WorldMapInfo | None:
        """获取世界地图信息（用于路径规划距离计算）"""
        self._ensure_npc_loaded()
        return self._npc_loader.get_world_map(map_id)

    def add_points(self, map_id: str, points: list[NpcPoint]) -> int:
        """添加点位到指定地图

        如果 refresh_id 已存在则覆盖更新。

        Args:
            map_id: 地图ID
            points: 要添加的点位列表

        Returns:
            实际新增的点位数量（不包含覆盖更新）
        """
        self._ensure_npc_loaded()
        return self._npc_loader.add_points(map_id, points)

    def get_refresh_rules_dict(self) -> dict[int, NpcRefreshRule]:
        """获取所有刷新规则字典（用于导入）"""
        self._ensure_npc_loaded()
        return self._npc_loader.get_refresh_rules_dict()
