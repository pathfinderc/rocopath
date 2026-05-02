# 直接导入编译好的 UI 代码（标准包导入，适配 src 结构）
from enum import Enum, auto
from PySide6.QtCore import Signal, QPointF, QRectF, Qt
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent, QPen, QBrush, QColor
from rocopath.ui.npc_point_item import NpcPointItem
from rocopath.ui.path_point_item import PathPointItem


class InteractionMode(Enum):
    NORMAL = auto()
    ADD_PATH = auto()


# 自定义可缩放/拖拽的视图
class MapView(QGraphicsView):
    """支持滚轮缩放（以鼠标为中心）和左键拖拽的地图视图
    额外支持：框选模式下右键框选点位用于路径规划。
    ADD_PATH 模式：左键点击创建路径点，中键拖拽平移。
    """

    mouse_moved = Signal(QPointF)
    box_selection_finished = Signal(QRectF, Qt.KeyboardModifier)
    point_clicked = Signal(NpcPointItem)
    path_point_created = Signal(QPointF)
    path_point_clicked = Signal(PathPointItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 启用抗锯齿与平滑缩放
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        # 禁用滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 设置默认光标为箭头
        self.setCursor(Qt.CursorShape.ArrowCursor)
        # 禁用内置拖拽模式，我们自己处理来控制光标
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # 允许鼠标追踪，无需按下按键也能触发 moveEvent
        self.setMouseTracking(True)
        # 拖拽状态
        self._panning = False
        self._last_pan_pos = QPointF()
        # 中键拖拽状态
        self._mid_panning = False
        self._mid_last_pan_pos = QPointF()
        # 缩放范围限制
        self._zoom_factor = 1.15
        self._min_scale = 0.2
        self._max_scale = 1.5
        # 框选状态
        self._is_box_dragging = False
        self._box_start_scene = QPointF()
        self._box_current_scene = QPointF()
        # 交互模式
        self._interaction_mode: InteractionMode = InteractionMode.NORMAL

    def set_interaction_mode(self, mode: InteractionMode) -> None:
        self._interaction_mode = mode

    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件：以鼠标位置为中心进行缩放"""
        # 获取鼠标在视图坐标系中的位置
        view_pos = event.position()
        # 转换为场景坐标（缩放前的场景坐标）
        scene_pos = self.mapToScene(view_pos.toPoint())

        # 计算缩放比例
        delta = event.angleDelta().y()
        if delta > 0:
            factor = self._zoom_factor
        else:
            factor = 1 / self._zoom_factor

        # 应用缩放
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        if self._min_scale <= new_scale <= self._max_scale:
            self.scale(factor, factor)

        # 将之前鼠标下的场景点重新定位到鼠标位置，实现以鼠标为中心的缩放效果
        new_view_pos = self.mapFromScene(scene_pos)
        delta_pos = view_pos - new_view_pos
        self.translate(delta_pos.x(), delta_pos.y())

        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下：
        - 左键 NORMAL：拖拽 / 点选点位
        - 左键 ADD_PATH：创建路径点 / 拖拽路径点
        - 中键：拖拽平移（ADD_PATH 模式下主要平移方式）
        - 右键：框选（始终可用）
        """
        # 中键拖拽平移（任何模式都支持）
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mid_panning = True
            self._mid_last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # 右键开始框选（始终启用）
        if event.button() == Qt.MouseButton.RightButton:
            self._is_box_dragging = True
            self._box_start_scene = self.mapToScene(event.position().toPoint())
            self._box_current_scene = self._box_start_scene
            event.accept()
            return

        # 左键点击
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            items = self.scene().items(scene_pos)

            # 检测是否点击了点位
            # ADD_PATH 模式下点击路径点不发送选中信号，由拖拽逻辑处理
            if self._interaction_mode != InteractionMode.ADD_PATH:
                for item in items:
                    if isinstance(item, NpcPointItem):
                        self.point_clicked.emit(item)
                    elif isinstance(item, PathPointItem):
                        self.path_point_clicked.emit(item)

            if self._interaction_mode == InteractionMode.ADD_PATH:
                # ADD_PATH 模式：空白处创建路径点
                has_point_item = any(
                    isinstance(item, (NpcPointItem, PathPointItem))
                    for item in items
                )
                if not has_point_item:
                    self.path_point_created.emit(scene_pos)
                # 不启动左键拖拽平移
            else:
                # NORMAL 模式：开始拖拽平移
                if not self._is_box_dragging:
                    self._panning = True
                    self._last_pan_pos = event.position()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动：拖拽时平移地图 / 框选时更新矩形"""
        if self._is_box_dragging:
            self._box_current_scene = self.mapToScene(event.position().toPoint())
            self.viewport().update()
            event.accept()

        if self._panning:
            current_pos = event.position()
            delta = current_pos - self._last_pan_pos
            self._last_pan_pos = current_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()

        if self._mid_panning:
            current_pos = event.position()
            delta = current_pos - self._mid_last_pan_pos
            self._mid_last_pan_pos = current_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()

        # 将视图坐标转换为场景坐标并发射信号
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放：结束拖拽 / 结束框选"""
        if self._is_box_dragging:
            if event.button() == Qt.MouseButton.RightButton:
                rect = self._get_selection_rect()
                modifiers = event.modifiers()
                self.box_selection_finished.emit(rect, modifiers)
                self._is_box_dragging = False
                self.viewport().update()
                event.accept()
                return

        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()

        if event.button() == Qt.MouseButton.MiddleButton:
            self._mid_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()

        super().mouseReleaseEvent(event)

    def _get_selection_rect(self) -> QRectF:
        """获取当前框选矩形（场景坐标）"""
        x1, y1 = self._box_start_scene.x(), self._box_start_scene.y()
        x2, y2 = self._box_current_scene.x(), self._box_current_scene.y()
        return QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    def paintEvent(self, event):
        """绘制：如果正在框选，绘制半透明矩形框"""
        super().paintEvent(event)

        if self._is_box_dragging:
            painter = QPainter(self.viewport())
            rect = self._get_selection_rect()
            top_left = self.mapFromScene(rect.topLeft())
            bottom_right = self.mapFromScene(rect.bottomRight())
            painter_rect = QRectF(top_left, bottom_right).normalized()

            painter.setPen(QPen(QColor(100, 149, 237, 255), 2))
            painter.setBrush(QBrush(QColor(100, 149, 237, 50)))
            painter.drawRect(painter_rect)
            painter.end()
