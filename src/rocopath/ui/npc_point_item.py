"""
NPC点位图形项

在 QGraphicsScene 中显示可点击的NPC点位标记。
支持默认圆形标记，根据颜色规则自动匹配自定义颜色。
预留未来自定义图标扩展。
"""

from dataclasses import dataclass
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsEllipseItem, QGraphicsPixmapItem
from PySide6.QtGui import QBrush, QColor, QPen, QPixmap
from rocopath.models import NpcPoint


# 点位默认样式配置
DEFAULT_RADIUS = 4
DEFAULT_NORMAL_COLOR = QColor(230, 40, 40, 255)  # 纯红色，完全不透明
SELECTED_COLOR = QColor(40, 200, 40, 255)  # 纯绿色，完全不透明
HOVER_COLOR = QColor(255, 140, 0, 255)  # 橙色，完全不透明


@dataclass
class PointColorRule:
    """点位颜色匹配规则：rule_ids任意匹配 AND 关键词任意匹配 → 应用颜色"""
    rule_ids: list[int]
    keywords: list[str]
    color: QColor


# 全局颜色规则列表 - 按顺序匹配，第一个匹配生效
POINT_COLOR_RULES: list[PointColorRule] = [
    PointColorRule([46, 8], ["黄石榴石"], QColor(255, 215, 0, 255)),
    PointColorRule([46, 8], ["黑晶琉璃"], QColor(40, 40, 40, 255)),
    PointColorRule([46, 8], ["紫莲刚玉"], QColor(148, 0, 211, 255)),
    PointColorRule([46, 8], ["蓝晶碧玺"], QColor(30, 144, 255, 255)),
    PointColorRule([2,5], ["眠枭之星","眠枭石像 - 终点 - 大型"], QColor(30, 144, 255, 255)),
    PointColorRule([5,7], ["NPC预设露营点/枯枝"], QColor(255, 0, 255, 255)),
    PointColorRule([2,5], ["型庇护所"], QColor(34, 139, 34, 255)),
    PointColorRule([2,5], ["音乐光点"], QColor(255, 215, 0, 255)),
    PointColorRule([2,5], ["普通火盆"], QColor(255, 140, 0, 255)),
    PointColorRule([2,5], ["扭蛋机"], QColor(220, 20, 60, 255)),
]


class NpcPointItem(QObject, QGraphicsItemGroup):
    """NPC点位图形项

    组合图形项，支持：
    - 默认圆形标记
    - 未来可扩展自定义图标图片
    - 可点击选中，发出信号
    """

    point_selected = Signal(int)  # 发出选中的 refresh_id

    def __init__(self, point: NpcPoint, radius: float = DEFAULT_RADIUS):
        QObject.__init__(self)
        QGraphicsItemGroup.__init__(self)
        self.refresh_id = point.refresh_id
        self.npc_point = point
        self._radius = radius
        self._is_selected = False

        # 路径规划选择状态
        self._in_box_selection = False  # 是否在框选集合中
        self._is_route_start = False   # 是否是路径起点

        # 根据颜色规则匹配自定义颜色
        normal_color = DEFAULT_NORMAL_COLOR
        for rule in POINT_COLOR_RULES:
            if point.refresh_rule.id in rule.rule_ids:
                if any(k in point.display_name for k in rule.keywords):
                    normal_color = rule.color
                    break

        # 创建圆形标记，中心在 (0, 0)
        self._ellipse = QGraphicsEllipseItem(
            -radius, -radius, radius * 2, radius * 2, self
        )
        self._normal_brush = QBrush(normal_color)
        self._original_normal_color = normal_color  # 保存原始颜色
        self._update_visual_style()

        # 预留未来自定义图标位置
        self._pixmap_item: QGraphicsPixmapItem | None = None

        # 设置整体位置：点位中心在 (map_x, map_y)
        self.setPos(point.map_x, point.map_y)

        # 设置可交互
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIsFocusable, True)
        # 禁用变换：点位不随地图缩放，保持固定像素大小
        self.setFlag(QGraphicsItemGroup.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptHoverEvents(True)

        # Z序：点位在地图之上
        self.setZValue(10)

    def mousePressEvent(self, event):
        """鼠标点击：发出选中信号"""
        self.point_selected.emit(self.refresh_id)
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        """鼠标进入"""
        self._ellipse.setBrush(QBrush(HOVER_COLOR))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """鼠标离开"""
        if self._is_selected:
            self._ellipse.setBrush(QBrush(SELECTED_COLOR))
        else:
            self._ellipse.setBrush(self._normal_brush)
        super().hoverLeaveEvent(event)

    def set_selected(self, is_selected: bool) -> None:
        """设置选中状态，改变样式"""
        self._is_selected = is_selected
        self.setSelected(is_selected)
        if is_selected:
            self._ellipse.setBrush(QBrush(SELECTED_COLOR))
        else:
            self._ellipse.setBrush(self._normal_brush)

    def set_custom_pixmap(self, pixmap: QPixmap) -> None:
        """设置自定义图标（预留未来使用）"""
        if self._pixmap_item is None:
            self._pixmap_item = QGraphicsPixmapItem(self)
        self._pixmap_item.setPixmap(pixmap)
        # 将图片居中放置
        pw = pixmap.width()
        ph = pixmap.height()
        self._pixmap_item.setOffset(-pw // 2, -ph // 2)

    def _update_visual_style(self) -> None:
        """根据当前状态更新视觉样式（填充色 + 边框）"""
        # 确定填充颜色
        if self._is_route_start:
            # 起点使用紫色填充
            fill_color = QColor(128, 0, 128, 255)
        elif self._is_selected:
            # 选中查看信息使用绿色
            fill_color = SELECTED_COLOR
        else:
            # 正常使用匹配到的原始颜色
            fill_color = self._original_normal_color

        self._ellipse.setBrush(QBrush(fill_color))

        # 确定边框
        if self._in_box_selection:
            # 框选集合中：白色粗边框
            pen = QPen(QColor(255, 255, 255, 255), 2.5)
        else:
            # 正常：黑色细边框
            pen = QPen(QColor(0, 0, 0, 255), 1.5)

        self._ellipse.setPen(pen)

    def set_in_box_selection(self, in_selection: bool) -> None:
        """设置是否在框选集合中，更新视觉样式"""
        self._in_box_selection = in_selection
        self._update_visual_style()

    def set_route_start(self, is_start: bool) -> None:
        """设置是否是路径起点，更新视觉样式"""
        self._is_route_start = is_start
        self._update_visual_style()

    def reset_route_selection(self) -> None:
        """重置所有路径选择相关状态"""
        self._in_box_selection = False
        self._is_route_start = False
        self._update_visual_style()

    @property
    def is_in_box_selection(self) -> bool:
        return self._in_box_selection
