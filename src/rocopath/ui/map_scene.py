"""
地图场景
继承 QGraphicsScene，封装点位管理、路径绘制和选择操作。

遵循 Qt Graphics View 框架设计：
- Scene 管数据和图元管理
- View 管显示和用户交互
"""

from dataclasses import dataclass
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PySide6.QtGui import QPixmap, QPainterPath, QPen, QColor, QBrush
from rocopath.ui.npc_point_item import NpcPointItem
from rocopath.core.route_planner import NearestNeighborPlanner, BaseRoutePlanner
from rocopath.models import NpcPoint, WorldMapInfo


@dataclass
class PlannedRoute:
    """已规划的路径"""

    points: list[NpcPoint]  # 路径点位列表
    total_distance: float  # 总距离
    color: tuple[int, int, int, int]  # 路径颜色 (RGBA)
    path_item: QGraphicsPathItem | None = None  # 绘制的路径线
    text_item: QGraphicsPathItem | None = None  # 起点序号文字标识（带轮廓）


class MapScene(QGraphicsScene):
    """地图场景，管理点位、路径和选择状态"""

    # 点位被点击选中（显示信息）时发出信号，参数是 refresh_id
    point_selected = Signal(int)

    # 预定义路径颜色，循环使用（RGBA，alpha=200 半透明）
    _ROUTE_COLORS: list[tuple[int, int, int, int]] = [
        (255, 0, 0, 200),  # 红
        (0, 150, 255, 200),  # 蓝
        (0, 200, 0, 200),  # 绿
        (255, 140, 0, 200),  # 橙
        (148, 0, 211, 200),  # 紫
        (255, 0, 255, 200),  # 粉
        (0, 200, 200, 200),  # 青
    ]

    def __init__(self, route_planner: BaseRoutePlanner | None = None):
        super().__init__()
        # 当前显示的点位项
        self._point_items: list[NpcPointItem] = []
        # 路径规划相关状态
        self._route_selected_refresh_ids: set[int] = set()
        self._route_start_point: NpcPoint | None = None
        # 已规划的路径列表（支持多条路径）
        self._planned_routes: list[PlannedRoute] = []
        # 路径规划算法
        self._route_planner: BaseRoutePlanner = (
            route_planner or NearestNeighborPlanner()
        )

    def add_background_pixmap(self, pixmap: QPixmap) -> None:
        """添加背景地图图片"""
        self.clear()
        self._point_items.clear()
        self.clear_route_selection_and_routes()
        self.addPixmap(pixmap)
        self.setSceneRect(pixmap.rect())

    def add_points(self, points: list[NpcPoint]) -> None:
        """添加多个点位到场景"""
        for point in points:
            item = NpcPointItem(point)
            self.addItem(item)
            self._point_items.append(item)
            # 转发点位点击信号
            item.point_selected.connect(self.point_selected.emit)

    def clear_points(self) -> None:
        """清除所有点位"""
        for item in self._point_items:
            self.removeItem(item)
        self._point_items.clear()
        self.clear_route_selection_and_routes()

    def select_all(self) -> None:
        """全选所有当前点位"""
        for item in self._point_items:
            if item.refresh_id not in self._route_selected_refresh_ids:
                self._route_selected_refresh_ids.add(item.refresh_id)
                item.set_in_box_selection(True)

        self._route_start_point = None

    def clear_route_selection(self) -> None:
        """清空所有路径选择状态（保留已规划路径）"""
        # 重置所有点位视觉状态
        for item in self._point_items:
            item.reset_route_selection()
        # 清空状态
        self._route_selected_refresh_ids.clear()
        self._route_start_point = None

    def clear_route_selection_and_routes(self) -> None:
        """清空所有路径选择状态和已规划路径"""
        self.clear_route_selection()
        self.clear_all_routes()

    def handle_box_selection(
        self, rect: QRectF, modifiers: Qt.KeyboardModifier
    ) -> None:
        """处理框选完成，更新选中状态"""
        remove_mode = modifiers & Qt.KeyboardModifier.ControlModifier

        for item in self._point_items:
            pos = item.scenePos()
            if rect.contains(pos):
                if remove_mode:
                    if item.refresh_id in self._route_selected_refresh_ids:
                        self._route_selected_refresh_ids.discard(item.refresh_id)
                        item.set_in_box_selection(False)
                        item.set_route_start(False)
                        if (
                            self._route_start_point
                            and self._route_start_point.refresh_id == item.refresh_id
                        ):
                            self._route_start_point = None
                else:
                    if item.refresh_id not in self._route_selected_refresh_ids:
                        self._route_selected_refresh_ids.add(item.refresh_id)
                        item.set_in_box_selection(True)

    def handle_point_click(self, item: NpcPointItem) -> None:
        """处理点选，切换选中状态"""
        if item.refresh_id in self._route_selected_refresh_ids:
            self._route_selected_refresh_ids.discard(item.refresh_id)
            item.set_in_box_selection(False)
            # 如果移除的是起点，清空起点
            if (
                self._route_start_point
                and self._route_start_point.refresh_id == item.refresh_id
            ):
                self._route_start_point = None
                item.set_route_start(False)
        else:
            self._route_selected_refresh_ids.add(item.refresh_id)
            item.set_in_box_selection(True)

    def set_route_start(self, point: NpcPoint) -> None:
        """设置路径起点"""
        # 先清除之前起点状态
        if self._route_start_point:
            for item in self._point_items:
                if item.refresh_id == self._route_start_point.refresh_id:
                    item.set_route_start(False)
                    break

        # 设置新起点
        self._route_start_point = point
        for item in self._point_items:
            if item.refresh_id == point.refresh_id:
                item.set_route_start(True)
                break

    def add_route_path(self, points: list[NpcPoint], total_distance: float) -> None:
        """添加并绘制一条新路径折线（保留已有路径）"""
        if len(points) < 2:
            return

        # 选择颜色：按顺序循环使用颜色列表
        color_index = len(self._planned_routes) % len(self._ROUTE_COLORS)
        color = self._ROUTE_COLORS[color_index]

        # 创建路径
        path = QPainterPath()
        first = points[0]
        path.moveTo(first.map_x, first.map_y)
        for point in points[1:]:
            path.lineTo(point.map_x, point.map_y)

        # 创建图形项
        path_item = QGraphicsPathItem(path)
        # 使用对应颜色粗线条，半透明
        pen = QPen(QColor(*color), 3)
        pen.setCosmetic(True)  # 缩放时保持线宽不变
        path_item.setPen(pen)
        path_item.setZValue(5)  # 在地图之上，点位之下
        self.addItem(path_item)

        # 添加起点序号文字标识（带黑色轮廓，固定大小忽略缩放）
        route_number = len(self._planned_routes) + 1
        text = str(route_number)

        # 使用 QPainterPath 创建带轮廓的文字
        font = self.font()
        font.setPointSize(14)
        font.setBold(True)
        text_path = QPainterPath()
        text_path.addText(0, 0, font, text)

        # 文字使用路径颜色填充，黑色轮廓
        brush = QBrush(QColor(*color))
        text_pen = QPen(QColor(0, 0, 0), 2)

        text_item = QGraphicsPathItem(text_path)
        text_item.setBrush(brush)
        text_item.setPen(text_pen)
        # 忽略变换，保持固定大小，不受地图缩放影响
        text_item.setFlag(
            QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations, True
        )
        # 在起点向右上方偏移
        text_item.setPos(first.map_x + 6, first.map_y - 16)
        text_item.setZValue(6)  # 在路径之上，点位之下
        self.addItem(text_item)

        # 添加到路径列表
        route = PlannedRoute(
            points=points,
            total_distance=total_distance,
            color=color,
            path_item=path_item,
            text_item=text_item,
        )
        self._planned_routes.append(route)

    def clear_all_routes(self) -> None:
        """清除所有已规划路径"""
        for route in self._planned_routes:
            if route.path_item and route.path_item.scene() == self:
                self.removeItem(route.path_item)
            if route.text_item and route.text_item.scene() == self:
                self.removeItem(route.text_item)
        self._planned_routes.clear()

    def clear_route_path(self) -> None:
        """清除路径（保留兼容调用，实际清除所有路径）"""
        self.clear_all_routes()

    # === Getter 方法供 MainWindow 获取状态更新 UI ===

    def get_selected_count(self) -> int:
        """获取选中点位数量"""
        return len(self._route_selected_refresh_ids)

    def get_route_start(self) -> NpcPoint | None:
        """获取当前路径起点"""
        return self._route_start_point

    def get_selected_points(self) -> list[NpcPoint]:
        """获取所有选中的点位"""
        selected: list[NpcPoint] = []
        for item in self._point_items:
            if item.refresh_id in self._route_selected_refresh_ids:
                selected.append(item.npc_point)
        return selected

    def get_all_current_points(self) -> list[NpcPoint]:
        """获取所有当前显示的点位"""
        all_points: list[NpcPoint] = []
        for item in self._point_items:
            all_points.append(item.npc_point)
        return all_points

    def has_point_items(self) -> bool:
        """是否有任何点位"""
        return len(self._point_items) > 0

    def is_selected(self, refresh_id: int) -> bool:
        """检查该点位是否已被选中"""
        return refresh_id in self._route_selected_refresh_ids

    def set_selected(self, refresh_id: int) -> None:
        """设置信息选中状态，更新所有点位视觉样式"""
        for item in self._point_items:
            item.set_selected(item.refresh_id == refresh_id)

    def get_planned_routes(self) -> list[PlannedRoute]:
        """获取所有已规划的路径"""
        return self._planned_routes

    def has_planned_routes(self) -> bool:
        """是否有已规划的路径"""
        return len(self._planned_routes) > 0

    def remove_route(self, route: PlannedRoute) -> None:
        """删除单条已规划路径"""
        if route.path_item and route.path_item.scene() == self:
            self.removeItem(route.path_item)
        if route.text_item and route.text_item.scene() == self:
            self.removeItem(route.text_item)
        if route in self._planned_routes:
            self._planned_routes.remove(route)

    def add_planned_route(
        self,
        points: list[NpcPoint],
        total_distance: float,
        color: tuple[int, int, int, int] | None = None,
    ) -> None:
        """添加一条已规划路径，自动绘制
        如果指定 color 则使用该颜色，否则自动分配下一个颜色
        """
        if color is not None:
            # 使用指定颜色
            route = PlannedRoute(
                points=points,
                total_distance=total_distance,
                color=color,
                path_item=None,
                text_item=None,
            )
            self._planned_routes.append(route)
            # 创建并添加图形项
            if len(points) < 2:
                return

            path = QPainterPath()
            first = points[0]
            path.moveTo(first.map_x, first.map_y)
            for point in points[1:]:
                path.lineTo(point.map_x, point.map_y)

            path_item = QGraphicsPathItem(path)
            pen = QPen(QColor(*color), 3)
            pen.setCosmetic(True)
            path_item.setPen(pen)
            path_item.setZValue(5)
            self.addItem(path_item)
            route.path_item = path_item

            # 添加起点序号文字标识（带黑色轮廓，固定大小忽略缩放），序号就是当前列表中的位置
            route_number = len(self._planned_routes)
            text = str(route_number)

            font = self.font()
            font.setPointSize(14)
            font.setBold(True)
            text_path = QPainterPath()
            text_path.addText(0, 0, font, text)

            brush = QBrush(QColor(*color))
            text_pen = QPen(QColor(0, 0, 0), 1)

            text_item = QGraphicsPathItem(text_path)
            text_item.setBrush(brush)
            text_item.setPen(text_pen)
            text_item.setFlag(
                QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations, True
            )
            text_item.setPos(first.map_x + 6, first.map_y - 16)
            text_item.setZValue(6)
            self.addItem(text_item)
            route.text_item = text_item
        else:
            # 自动分配颜色
            self.add_route_path(points, total_distance)

    def plan_route(self, world_map: WorldMapInfo) -> tuple[list[NpcPoint], float]:
        """规划路径，返回规划好的点位列表和总距离

        Args:
            world_map: 世界地图信息，用于计算距离

        Returns:
            (planned_points, total_distance)
        """
        start_point = self.get_route_start()
        selected_points = self.get_selected_points()
        if not start_point or len(selected_points) < 2:
            return [], 0.0

        # 执行规划
        planned_path = self._route_planner.plan(selected_points, start_point, world_map)

        # 计算总距离
        total_distance = 0.0
        for i in range(len(planned_path) - 1):
            total_distance += self._route_planner.distance(
                planned_path[i], planned_path[i + 1], world_map
            )

        # 添加并绘制路径（保留已有路径）
        self.add_route_path(planned_path, total_distance)

        return planned_path, total_distance
