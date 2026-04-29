"""
主窗口

负责UI事件处理，调用 Controller 执行业务逻辑，显示结果。
"""

import os
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QMessageBox, QDialog, QLabel, QPushButton,
    QFileDialog, QFormLayout, QLineEdit
)
from PySide6.QtGui import QPixmap
from loguru import logger

from rocopath.ui import Ui_MainWindow
from rocopath.utils import pil_image_to_qimage
from rocopath.ui.map_view import MapView
from rocopath.ui.map_scene import MapScene, PlannedRoute
from rocopath.ui.npc_point_item import NpcPointItem
from rocopath.ui.filter_panel import FilterPanel
from rocopath.core.map_controller import MapController
from rocopath.exporters.compatible import generate_compatible_json
from rocopath.exporters.compatible_new import generate_new_compatible_json
from rocopath.exporters.npc_imp_exp import (
    generate_npc_export_json,
    generate_route_export_json,
    parse_npc_import_json,
    rebuild_npc_points
)
from rocopath.models import NpcPoint
from rocopath.config import BIGWORLD_MAP_ID


class MainWindow(QMainWindow):
    def __init__(self, map_controller: MapController):
        super().__init__()
        # 依赖注入：控制器由外部创建传入
        self.map_controller = map_controller
        # 加载 UI 设计文件
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 当前地图ID
        self._current_map_id: str = ""
        # 当前点击选中查看信息的点位
        self._selected_point: NpcPoint | None = None
        # 基础点位集合 - 只由 checkbox 筛选结果决定，line_search 不修改它
        self._base_points: list[NpcPoint] | None = None
        # 筛选面板（处理快捷筛选和规则筛选）
        self._filter_panel: FilterPanel | None = None
        # 地图场景（管理点位、路径、选择状态）
        self.map_scene: MapScene

        # 更新 UI 元素
        self.update_ui()

    def update_ui(self):
        """初始化所有UI元素"""
        self._init_map_view()
        self._set_search_group()
        self._set_point_filter()
        self._connect_menu_actions()
        self._connect_search()
        self._connect_route_planning()
        self._set_help_text()
        self.load_map(BIGWORLD_MAP_ID)

    def _set_search_group(self):
        """设置搜索框事件处理"""
        # 回车也触发搜索
        self.ui.line_search.returnPressed.connect(self._do_search)

    def _set_point_filter(self):
        """创建筛选面板并构建UI"""
        # 获取所有刷新规则
        rules = self.map_controller.get_all_refresh_rules()
        # 创建筛选面板并构建
        self._filter_panel = FilterPanel(
            tab_widget=self.ui.tabWidget,
            on_filter_changed=self._on_filter_changed,
            on_keywords_changed=self._on_keywords_changed
        )
        self._filter_panel.build(rules)

    def _on_keywords_changed(self, keywords: str) -> None:
        """关键词变化：更新搜索框文本"""
        self.ui.line_search.setText(keywords)

    def _connect_menu_actions(self):
        """连接菜单栏动作"""
        # 切换地图
        from rocopath.config import MAGIC_ACADEMY_MAP_ID, BIGWORLD_MAP_ID
        self.ui.action_main_map.triggered.connect(lambda: self.load_map(BIGWORLD_MAP_ID))
        self.ui.action_magic_map.triggered.connect(lambda: self.load_map(MAGIC_ACADEMY_MAP_ID))
        # 键位说明
        self.ui.action_key.triggered.connect(self._show_key_bindings)
        # 关于
        self.ui.action_about.triggered.connect(self._show_about)
        # 兼容格式导出
        self.ui.action_compatible_export.triggered.connect(self._on_compatible_export)
        # 新兼容格式导出
        self.ui.action_new_compatible_export.triggered.connect(self._on_new_compatible_export)
        # 导出文件（完整NPC点位导出）
        self.ui.action_export.triggered.connect(self._on_npc_export)
        # 导出当前显示点位
        self.ui.action_export_point.triggered.connect(self._on_export_current_points)
        # 导出所有已规划路径
        self.ui.action_export_route.triggered.connect(self._on_export_routes)
        # 导入点位
        self.ui.action_import.triggered.connect(self._on_npc_import)

    def _connect_search(self):
        """连接搜索按钮"""
        self.ui.search_button.clicked.connect(self._do_search)

    def _connect_route_planning(self):
        """连接路径规划相关UI信号"""
        # 全选/清空按钮
        self.ui.select_all.clicked.connect(self._on_select_all_clicked)
        self.ui.clear_select.clicked.connect(self._on_clear_select_clicked)
        self.ui.reset_all.clicked.connect(self._on_reset_route_selection_clicked)
        # 规划路径按钮（选择起点简化为自动）
        self.ui.plan_route.clicked.connect(self._on_plan_route_clicked)
        # 合并路径和删除选中点
        self.ui.merge_select.clicked.connect(self._on_merge_select_clicked)
        self.ui.remove_select.clicked.connect(self._on_remove_select_clicked)
        # MapView 信号
        self.map_view.box_selection_finished.connect(self._handle_box_selection)
        self.map_view.point_clicked.connect(self._handle_point_click)
        # 初始化UI状态
        self._update_route_ui_state()

    def load_map(self, map_id: str) -> bool:
        """
        通过控制器加载并显示地图

        Returns:
            加载成功返回 True，失败返回 False
        """
        map_info = self.map_controller.load_map(map_id)
        if map_info is None or map_info.image is None:
            logger.warning("地图加载失败: {}", map_id)
            return False

        self._current_map_id = map_id
        q_image = pil_image_to_qimage(map_info.image)
        # 转 QPixmap（给 QGraphicsView 显示）
        pixmap = QPixmap.fromImage(q_image)

        # 先清点位（从列表移除，避免删除已经被scene.clear删除的对象）
        self._clear_point_items()
        self._clear_point_info()
        # 切换地图清空路径规划选择
        self._clear_route_selection()

        # 清除旧内容添加新地图
        self.map_scene.add_background_pixmap(pixmap)
        # 将视图中心定位到图片中心
        self.map_view.centerOn(self.map_scene.sceneRect().center())
        # 更新窗口标题
        self.setWindowTitle(f"洛寻 - {map_info.name}")
        return True

    def _init_map_view(self):
        """初始化地图视图"""
        group_box = self.ui.map_group
        layout = QVBoxLayout(group_box)
        self.map_view = MapView()
        layout.addWidget(self.map_view)

        self.map_scene = MapScene()
        self.map_view.setScene(self.map_scene)
        self.map_view.mouse_moved.connect(self.update_status_bar_coordinates)
        # 连接点位选中信号（只需要连接一次）
        self.map_scene.point_selected.connect(self._on_point_selected)

    def update_status_bar_coordinates(self, scene_pos: QPointF):
        """更新状态栏显示当前场景坐标"""
        x = int(scene_pos.x())
        y = int(scene_pos.y())
        self.ui.statusbar.showMessage(f"坐标: ({x}, {y})")

    def _on_filter_changed(self):
        """筛选规则变化（checkbox 变化）：重新计算基础点位，清空搜索框，显示全部"""
        # checkbox 变化，清除所有路径规划选择和绘制
        self._clear_route_selection()
        # 清空搜索框，line_search 不影响基础点位
        self.ui.line_search.clear()
        # 重新计算基础点位
        self._rebuild_base_points()
        # 显示全部基础点位
        self._do_search()

    def _rebuild_base_points(self):
        """根据当前 checkbox 勾选状态重新计算基础点位集合

        QuickFilter 搜索逻辑：每个勾选的 QuickFilter 单独计算结果，最后取并集
        result = (quick_filter_1 result) ∪ (quick_filter_2 result) ∪ ...
        每个 quick_filter result = (rule in rule_ids) AND (name contains any keyword)
        最后如果有额外勾选的 rule_ids（来自 tab_3 手动勾选），再做一次规则筛选
        """
        if not self._current_map_id or not self._filter_panel:
            self._base_points = []
            return

        all_points = self.map_controller.get_all_points(self._current_map_id)
        selected_rule_ids = self._filter_panel.get_selected_rule_ids()
        selected_quick_filters = self._filter_panel.get_all_selected_quick_filters()

        logger.debug("重新计算基础点位: quick_filters={}, rule_ids={}",
                    len(selected_quick_filters), len(selected_rule_ids))

        # 如果没有勾选任何规则，清空
        if not selected_rule_ids:
            self._base_points = []
            self.ui.point_info.setText("请至少勾选一个刷新规则")
            logger.info("基础点位: 没有勾选任何规则 → 清空")
            return

        # 如果没有勾选 QuickFilter，只按 rule_ids 筛选
        if not selected_quick_filters:
            self._base_points = self.map_controller.filter_by_rule_ids(
                all_points, selected_rule_ids
            )
            logger.info("基础点位: 无 QuickFilter，按规则筛选 → {} 个点位", len(self._base_points))
            return

        # 每个勾选的 QuickFilter 单独计算，结果取并集
        result_set: dict[int, NpcPoint] = {}  # 使用 refresh_id 去重

        for qf in selected_quick_filters:
            # QuickFilter: (rule in rule_ids) AND (name contains any keyword)
            qf_result = self.map_controller.filter_by_rule_ids(all_points, qf.rule_ids)
            if qf.keywords and any(k.strip() for k in qf.keywords):
                qf_result = self.map_controller.filter_by_any_keyword(qf_result, qf.keywords)
            # 添加到结果集合（去重）
            for point in qf_result:
                result_set[point.refresh_id] = point

        # 将结果转为列表
        quick_result = list(result_set.values())

        # 最后按 tab_3 当前所有勾选的 rule_ids 再筛选一次
        # 保证 tab_3 手动勾选的规则会包含，取消勾选的会排除
        self._base_points = self.map_controller.filter_by_rule_ids(quick_result, selected_rule_ids)

        logger.info("基础点位: {} QuickFilters → {} 个点位",
                    len(selected_quick_filters), len(self._base_points))

    def _do_search(self):
        """执行搜索：line_search 在基础点位中进一步筛选，不修改 _base_points"""
        if not self._base_points:
            self._clear_point_items()
            if self._base_points is not None:
                self.ui.point_info.setText("未找到匹配点位")
            return

        keyword = self.ui.line_search.text().strip()

        if not keyword:
            # 关键词为空，显示全部基础点位
            points = self._base_points
        else:
            # 在基础点位中筛选
            points = self.map_controller.filter_by_keyword(self._base_points, keyword)

        logger.debug("line_search: keyword='{}' → base={}, result={}",
                    keyword, len(self._base_points), len(points))

        # 打印前5个点的坐标方便调试
        if points:
            sample = [f"({p.map_x:.1f}, {p.map_y:.1f})" for p in points[:5]]
            logger.debug("前5个点位坐标示例: {}", ", ".join(sample))

        self._clear_point_items()
        self._clear_point_info()
        # 搜索刷新点位后清空路径规划选择
        self._clear_route_selection()
        self._show_points(points)

        if not points:
            self.ui.point_info.setText("未找到匹配点位")

    def _clear_point_items(self):
        """清除当前显示的所有点位"""
        self.map_scene.clear_points()
        self._selected_point = None

    def _clear_point_info(self):
        """清除点位信息"""
        self.ui.point_info.clear()

    def _show_points(self, points: list[NpcPoint]):
        """在地图上显示搜索到的点位"""
        logger.debug("_show_points: 开始添加 {} 个点位到场景", len(points))
        self.map_scene.add_points(points)
        logger.debug("_show_points: 添加完成，当前共有 {} 个点位项", self.map_scene.get_selected_count())
        # 在状态栏显示找到的点位数量
        self.ui.statusbar.showMessage(f"共找到 {len(points)} 个点位")

    def _on_point_selected(self, refresh_id: int):
        """点位被点击：显示详情"""
        point = self.map_controller.get_point_by_refresh_id(
            self._current_map_id, refresh_id
        )
        if point is None:
            logger.warning("找不到点位: refresh_id={}", refresh_id)
            return

        # 更新选中样式（MapScene 内部维护点位列表，不需要遍历）
        self.map_scene.set_selected(refresh_id)

        self._selected_point = point
        self._show_point_info(point)

        # 如果该点位已被框选 → 自动设为路径起点（框选始终启用）
        if self.map_scene.is_selected(refresh_id):
            self._set_route_start(point)
            self.ui.statusbar.showMessage(f"起点已设置: {point.display_name}")

    def _show_point_info(self, point: NpcPoint):
        """在信息框显示点位详情"""
        info = (
            f"NPC 名称: {point.display_name}\n"
            f"\n"
            f"NPC ID: {point.npc.id}\n"
            f"编辑器名称: {point.npc.editor_name}\n"
            f"刷新点ID: {point.refresh_id}\n"
            f"刷新规则: {point.refresh_rule.id} - {point.refresh_rule.description}\n"
            f"地图ID: {point.area.map_id if point.area else '-'}\n"
            f"\n"
            f"世界坐标: {f'({point.area.world_x}, {point.area.world_y})' if point.area else '-'}\n"
            f"地图坐标: ({point.map_x:.0f}, {point.map_y:.0f})\n"
        )
        self.ui.point_info.setText(info)

    # === 路径规划功能 ===
    def _update_route_ui_state(self) -> None:
        """根据当前状态更新UI控件启用/禁用和显示文字"""
        has_selection = self.map_scene.get_selected_count() > 0
        has_routes = self.map_scene.has_planned_routes()

        # 更新标签文字
        self.ui.select_num.setText(f"选中点位: {self.map_scene.get_selected_count()}")
        start_point = self.map_scene.get_route_start()
        if start_point:
            self.ui.start_status.setText(f"起点: {start_point.display_name}")
        else:
            self.ui.start_status.setText("起点: 未选择")

        # 更新按钮启用状态
        # 简化设计：框选模式始终启用，不需要手动开关
        self.ui.select_all.setEnabled(True)
        # 清空选中状态：有选中点位时启用
        self.ui.clear_select.setEnabled(has_selection)
        # 清空全部：有选中点位 或者 有已规划路径 都启用
        self.ui.reset_all.setEnabled(has_selection or has_routes)
        # self.ui.select_start.setEnabled(False)  # 不再需要手动选择起点
        # 规划按钮：至少2个选中 + 起点已设置
        can_plan = (self.map_scene.get_selected_count() >= 2 and
                    start_point is not None)
        self.ui.plan_route.setEnabled(can_plan)


    def _on_select_all_clicked(self) -> None:
        """全选当前显示的所有点位"""
        self.map_scene.select_all()
        self._update_route_ui_state()
        logger.debug("全选完成，共 {} 个点位", self.map_scene.get_selected_count())

    def _on_clear_select_clicked(self) -> None:
        """清空选中状态，但保留已规划路径"""
        self._clear_route_selection()
        logger.debug("清空选中状态完成")
        self.ui.statusbar.showMessage("已清空选中状态")

    def _on_reset_route_selection_clicked(self) -> None:
        """清空所有路径选择和已规划路径"""
        self._clear_route_selection_and_routes()
        logger.debug("清空路径选择和所有已规划路径")

    def _clear_route_selection(self) -> None:
        """清空所有路径选择状态（保留已规划路径）"""
        self.map_scene.clear_route_selection()
        # 更新UI
        self._update_route_ui_state()

    def _clear_route_selection_and_routes(self) -> None:
        """清空所有路径选择和已规划路径"""
        self.map_scene.clear_route_selection_and_routes()
        # 更新UI
        self._update_route_ui_state()

    def _clear_route_path(self) -> None:
        """清除地图上绘制的路径"""
        self.map_scene.clear_route_path()

    def _handle_box_selection(self, rect: QRectF, modifiers: Qt.KeyboardModifier) -> None:
        """处理框选完成：添加或移除矩形内的点位"""
        self.map_scene.handle_box_selection(rect, modifiers)
        self._update_route_ui_state()
        count = self.map_scene.get_selected_count()
        remove_mode = modifiers & Qt.KeyboardModifier.ControlModifier
        logger.debug("框选完成: remove_mode={}, 现在共 {} 个选中",
                    remove_mode, count)

    def _handle_point_click(self, item: NpcPointItem) -> None:
        """处理点选：toggle 选中状态

        框选模式下左键点击点位：切换选中状态
        如果取消选中的是起点，自动清空起点
        """
        # 正常框选模式下 toggle 选中状态
        self.map_scene.handle_point_click(item)
        self._update_route_ui_state()

    def _set_route_start(self, point: NpcPoint) -> None:
        """设置路径起点"""
        self.map_scene.set_route_start(point)
        self._update_route_ui_state()

    def _on_plan_route_clicked(self) -> None:
        """点击规划路径按钮"""
        # 获取当前世界地图信息
        world_map = self.map_controller.get_world_map(self._current_map_id)
        if world_map is None:
            self.ui.statusbar.showMessage("无法获取地图信息，规划失败")
            return

        # 规划路径（MapScene 完成规划和绘制）
        planned_path, total_distance = self.map_scene.plan_route(world_map)
        if not planned_path:
            return

        # 更新状态栏
        self.ui.statusbar.showMessage(
            f"规划完成: 共 {len(planned_path)} 个点位，总距离 {total_distance:.1f}"
        )

        # 在信息框显示路径详情
        self._show_route_info(planned_path, total_distance)

        logger.debug("路径规划完成: {} 个点位，总距离 {:.1f}",
                    len(planned_path), total_distance)

        # 自动清空选中状态和起点，方便规划下一条路径
        self._clear_route_selection()


    def _show_route_info(self, points: list[NpcPoint], total_distance: float) -> None:
        """在信息框显示路径详情"""
        if not points:
            return

        lines = [f"规划路径: {len(points)} 个点位", f"总距离: {total_distance:.1f}", ""]
        for i, point in enumerate(points, 1):
            lines.append(f"{i}. {point.display_name}")

        info = "\n".join(lines)
        self.ui.point_info.setText(info)

    def _show_key_bindings(self):
        """显示键位说明对话框"""
        key_info = """左键点选地图标点
按住左键拖动地图
右键框选点位
Ctrl+右键取消框选点位
点击框选点位中的一个则自动设置为起点
设置起点后可以点击规划路径算出路径"""
        QMessageBox.information(
            self,
            "键位说明",
            key_info,
            QMessageBox.StandardButton.Ok
        )

    def _show_about(self):
        """显示关于对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("关于")
        dialog.setFixedSize(350, 180)

        layout = QVBoxLayout(dialog)

        label = QLabel("""<h3>洛寻 (rocopath)</h3>
<p>《洛克王国：世界》采集路径规划工具</p>
<p>项目地址：<br>
<a href="https://github.com/pathfinderc/rocopath">https://github.com/pathfinderc/rocopath</a></p>""")
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)

        layout.addWidget(label)
        layout.addWidget(ok_button)

        dialog.exec()

    def _on_new_compatible_export(self):
        """导出兼容格式JSON路径文件

        支持多条路径批量导出，直接使用已规划好的路径，不需要重新计算
        """
        # 获取所有已规划路径
        routes = self.map_scene.get_planned_routes()

        if not routes:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前没有已规划好的路径，请先规划至少一条路径",
                QMessageBox.StandardButton.Ok
            )
            return

        # 默认说明
        default_notes = "本路线从洛寻导出，可能与实际游戏资源点存在差异。"

        # 单条路径：保持原有对话框交互
        if len(routes) == 1:
            # 弹出输入对话框让用户输入 name 和 notes
            dialog = QDialog(self)
            dialog.setWindowTitle("导出兼容格式路径")
            dialog.setFixedSize(400, 180)
            layout = QFormLayout(dialog)

            name_edit = QLineEdit()
            name_edit.setPlaceholderText("例如：向阳花路线")
            layout.addRow("路径名称:", name_edit)

            notes_edit = QLineEdit()
            notes_edit.setText(default_notes)
            notes_edit.setDisabled(True)
            layout.addRow("路径说明:", notes_edit)

            ok_button = QPushButton("下一步...")
            ok_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("取消")
            cancel_button.clicked.connect(dialog.reject)

            button_layout = QVBoxLayout()
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addRow("", button_layout)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            name = name_edit.text().strip()
            notes = notes_edit.text().strip()

            if not name:
                QMessageBox.warning(
                    self,
                    "输入错误",
                    "路径名称不能为空",
                    QMessageBox.StandardButton.Ok
                )
                return

            # 直接使用已保存的路径，不需要重新计算
            route = routes[0]
            points = [(p.map_x, p.map_y) for p in route.points]

            # 生成 JSON
            json_str = generate_new_compatible_json(name, notes, points, loop=False)

            # 弹出保存文件对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存路径文件",
                f"{name}.json",
                "JSON 文件 (*.json);;所有文件 (*)"
            )

            if not file_path:
                return

            # 保存文件
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                logger.info("兼容格式导出成功: {}", file_path)
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"路径已成功导出到:\n{file_path}",
                    QMessageBox.StandardButton.Ok
                )
                self.ui.statusbar.showMessage(f"导出完成: {file_path}")
            except Exception as e:
                logger.error("导出文件失败: {}", str(e))
                QMessageBox.critical(
                    self,
                    "导出失败",
                    f"保存文件时出错:\n{str(e)}",
                    QMessageBox.StandardButton.Ok
                )
            return

        # 多条路径：批量导出
        # 弹出输入对话框让用户输入文件名前缀
        dialog = QDialog(self)
        dialog.setWindowTitle("批量导出兼容格式路径")
        dialog.setFixedSize(420, 160)
        layout = QFormLayout(dialog)

        prefix_edit = QLineEdit()
        prefix_edit.setText("route")
        prefix_edit.setPlaceholderText("文件名前缀，例如 route")
        layout.addRow("文件名前缀:", prefix_edit)

        notes_edit = QLineEdit()
        notes_edit.setText(default_notes)
        notes_edit.setDisabled(True)
        layout.addRow("路径说明:", notes_edit)

        ok_button = QPushButton("选择导出目录...")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)

        button_layout = QVBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow("", button_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        prefix = prefix_edit.text().strip() or "route"
        notes = notes_edit.text().strip()

        # 让用户选择输出目录
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not directory:
            return

        # 批量导出所有路径
        success_count = 0
        errors: list[str] = []

        for i, route in enumerate(routes, 1):
            # 文件名：prefix_1.json, prefix_2.json, ...
            filename = f"{prefix}_{i}.json"
            file_path = os.path.join(directory, filename)

            # 提取坐标
            points = [(p.map_x, p.map_y) for p in route.points]

            # 使用序号作为路径名称
            route_name = f"{prefix}_{i}" if len(routes) > 1 else prefix

            # 生成 JSON
            json_str = generate_new_compatible_json(route_name, notes, points, loop=False)

            # 保存文件
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                success_count += 1
                logger.info("批量导出成功: {}", file_path)
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
                logger.error("批量导出失败 {}: {}", filename, str(e))

        # 显示结果
        if not errors:
            QMessageBox.information(
                self,
                "批量导出成功",
                f"成功导出 {success_count} 条路径到目录:\n{directory}",
                QMessageBox.StandardButton.Ok
            )
            self.ui.statusbar.showMessage(f"批量导出完成: {success_count} 条路径")
        else:
            if success_count > 0:
                QMessageBox.warning(
                    self,
                    "部分导出失败",
                    f"成功: {success_count} 条\n失败: {len(errors)} 条\n\n" + "\n".join(errors),
                    QMessageBox.StandardButton.Ok
                )
                self.ui.statusbar.showMessage(f"导出完成: {success_count} 成功, {len(errors)} 失败")
            else:
                QMessageBox.critical(
                    self,
                    "全部导出失败",
                    "\n".join(errors),
                    QMessageBox.StandardButton.Ok
                )
                self.ui.statusbar.showMessage("导出失败")

    def _on_compatible_export(self):
        """导出兼容格式JSON路径文件

        支持多条路径批量导出，直接使用已规划好的路径，不需要重新计算
        """
        # 获取所有已规划路径
        routes = self.map_scene.get_planned_routes()

        if not routes:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前没有已规划好的路径，请先规划至少一条路径",
                QMessageBox.StandardButton.Ok
            )
            return

        # 默认说明
        default_notes = "本路线从洛寻导出，可能与实际游戏资源点存在差异。"

        # 单条路径：保持原有对话框交互
        if len(routes) == 1:
            # 弹出输入对话框让用户输入 name 和 notes
            dialog = QDialog(self)
            dialog.setWindowTitle("导出兼容格式路径")
            dialog.setFixedSize(400, 180)
            layout = QFormLayout(dialog)

            name_edit = QLineEdit()
            name_edit.setPlaceholderText("例如：向阳花路线")
            layout.addRow("路径名称:", name_edit)

            notes_edit = QLineEdit()
            notes_edit.setText(default_notes)
            notes_edit.setDisabled(True)
            layout.addRow("路径说明:", notes_edit)

            ok_button = QPushButton("下一步...")
            ok_button.clicked.connect(dialog.accept)
            cancel_button = QPushButton("取消")
            cancel_button.clicked.connect(dialog.reject)

            button_layout = QVBoxLayout()
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addRow("", button_layout)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            name = name_edit.text().strip()
            notes = notes_edit.text().strip()

            if not name:
                QMessageBox.warning(
                    self,
                    "输入错误",
                    "路径名称不能为空",
                    QMessageBox.StandardButton.Ok
                )
                return

            # 直接使用已保存的路径，不需要重新计算
            route = routes[0]
            points = [(p.map_x, p.map_y) for p in route.points]

            # 生成 JSON
            json_str = generate_compatible_json(name, notes, points, loop=False)

            # 弹出保存文件对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存路径文件",
                f"{name}.json",
                "JSON 文件 (*.json);;所有文件 (*)"
            )

            if not file_path:
                return

            # 保存文件
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                logger.info("兼容格式导出成功: {}", file_path)
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"路径已成功导出到:\n{file_path}",
                    QMessageBox.StandardButton.Ok
                )
                self.ui.statusbar.showMessage(f"导出完成: {file_path}")
            except Exception as e:
                logger.error("导出文件失败: {}", str(e))
                QMessageBox.critical(
                    self,
                    "导出失败",
                    f"保存文件时出错:\n{str(e)}",
                    QMessageBox.StandardButton.Ok
                )
            return

        # 多条路径：批量导出
        # 弹出输入对话框让用户输入文件名前缀
        dialog = QDialog(self)
        dialog.setWindowTitle("批量导出兼容格式路径")
        dialog.setFixedSize(420, 160)
        layout = QFormLayout(dialog)

        prefix_edit = QLineEdit()
        prefix_edit.setText("route")
        prefix_edit.setPlaceholderText("文件名前缀，例如 route")
        layout.addRow("文件名前缀:", prefix_edit)

        notes_edit = QLineEdit()
        notes_edit.setText(default_notes)
        notes_edit.setDisabled(True)
        layout.addRow("路径说明:", notes_edit)

        ok_button = QPushButton("选择导出目录...")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)

        button_layout = QVBoxLayout()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow("", button_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        prefix = prefix_edit.text().strip() or "route"
        notes = notes_edit.text().strip()

        # 让用户选择输出目录
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not directory:
            return

        # 批量导出所有路径
        success_count = 0
        errors: list[str] = []

        for i, route in enumerate(routes, 1):
            # 文件名：prefix_1.json, prefix_2.json, ...
            filename = f"{prefix}_{i}.json"
            file_path = os.path.join(directory, filename)

            # 提取坐标
            points = [(p.map_x, p.map_y) for p in route.points]

            # 使用序号作为路径名称
            route_name = f"{prefix}_{i}" if len(routes) > 1 else prefix

            # 生成 JSON
            json_str = generate_compatible_json(route_name, notes, points, loop=False)

            # 保存文件
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                success_count += 1
                logger.info("批量导出成功: {}", file_path)
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
                logger.error("批量导出失败 {}: {}", filename, str(e))

        # 显示结果
        if not errors:
            QMessageBox.information(
                self,
                "批量导出成功",
                f"成功导出 {success_count} 条路径到目录:\n{directory}",
                QMessageBox.StandardButton.Ok
            )
            self.ui.statusbar.showMessage(f"批量导出完成: {success_count} 条路径")
        else:
            if success_count > 0:
                QMessageBox.warning(
                    self,
                    "部分导出失败",
                    f"成功: {success_count} 条\n失败: {len(errors)} 条\n\n" + "\n".join(errors),
                    QMessageBox.StandardButton.Ok
                )
                self.ui.statusbar.showMessage(f"导出完成: {success_count} 成功, {len(errors)} 失败")
            else:
                QMessageBox.critical(
                    self,
                    "全部导出失败",
                    "\n".join(errors),
                    QMessageBox.StandardButton.Ok
                )
                self.ui.statusbar.showMessage("导出失败")

    def _on_npc_export(self):
        """导出当前地图所有NPC点位

        导出完整NPC点位信息，包含世界坐标、像素坐标、NPC信息等。
        """
        # 检查当前是否加载地图
        if not self._current_map_id:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前未加载任何地图，请先加载地图",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取世界地图信息
        world_map = self.map_controller.get_world_map(self._current_map_id)
        if not world_map:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前地图信息未加载，无法导出",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取所有NPC点位
        npc_points = self.map_controller.get_all_points(self._current_map_id)
        if not npc_points:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前地图没有可导出的NPC点位",
                QMessageBox.StandardButton.Ok
            )
            return

        # 弹出保存文件对话框
        map_name = world_map.name
        default_filename = f"{map_name}_npc_points.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出NPC点位",
            default_filename,
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        # 生成JSON
        json_str = generate_npc_export_json(
            self._current_map_id,
            map_name,
            world_map,
            npc_points
        )

        # 保存文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info("NPC点位导出成功: {}", file_path)
            QMessageBox.information(
                self,
                "导出成功",
                f"已成功导出 {len(npc_points)} 个NPC点位到:\n{file_path}",
                QMessageBox.StandardButton.Ok
            )
            self.ui.statusbar.showMessage(f"导出完成: {file_path}")
        except Exception as e:
            logger.error("导出NPC点位失败: {}", str(e))
            QMessageBox.critical(
                self,
                "导出失败",
                f"保存文件时出错:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def _on_npc_import(self):
        """导入NPC点位文件

        从导出的JSON文件中导入点位，与当前地图现有点位合并。
        """
        # 检查当前是否加载地图
        if not self._current_map_id:
            QMessageBox.warning(
                self,
                "无法导入",
                "请先加载目标地图，再导入点位",
                QMessageBox.StandardButton.Ok
            )
            return

        # 弹出打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入NPC点位",
            "",
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        # 读取并解析文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
        except Exception as e:
            logger.error("读取导入文件失败: {}", str(e))
            QMessageBox.critical(
                self,
                "读取失败",
                f"读取文件时出错:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )
            return

        # 解析JSON
        try:
            map_info, points_data = parse_npc_import_json(json_content)
        except ValueError as e:
            logger.error("解析导入JSON失败: {}", str(e))
            QMessageBox.critical(
                self,
                "格式错误",
                f"文件格式不正确:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )
            return

        if not points_data:
            QMessageBox.warning(
                self,
                "没有点位",
                "文件中没有可导入的NPC点位",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取刷新规则字典
        refresh_rules = self.map_controller.get_refresh_rules_dict()

        # 重建 NpcPoint 对象
        npc_points = rebuild_npc_points(
            points_data,
            self._current_map_id,
            refresh_rules
        )

        # 弹出确认对话框
        reply = QMessageBox.question(
            self,
            "确认导入",
            f"检测到 {len(npc_points)} 个点位\n"
            f"导入会与当前地图现有点位合并，已存在的 refresh_id 会被覆盖。\n\n"
            f"是否继续导入？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 添加到地图
        added = self.map_controller.add_points(self._current_map_id, npc_points)
        total = len(npc_points)
        updated = total - added

        logger.info("NPC点位导入完成: 新增={}, 更新={}", added, updated)

        # 重新显示点位
        self._rebuild_base_points()
        self._do_search()

        # 显示结果
        QMessageBox.information(
            self,
            "导入完成",
            f"导入完成:\n新增 {added} 个点位\n更新 {updated} 个已存在点位\n\n"
            f"当前地图共 {len(self.map_controller.get_all_points(self._current_map_id))} 个点位",
            QMessageBox.StandardButton.Ok
        )
        self.ui.statusbar.showMessage(
            f"导入完成: 新增 {added}, 更新 {updated}"
        )

    def _on_export_current_points(self):
        """导出当前地图显示的点位

        只导出当前经过筛选后显示在地图上的点位，不导出全部点位。
        """
        # 检查当前是否加载地图
        if not self._current_map_id:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前未加载任何地图，请先加载地图",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取当前显示的所有点位
        points = self.map_scene.get_all_current_points()
        if not points:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前地图没有显示任何点位，请先搜索或筛选出要导出的点位",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取世界地图信息
        world_map = self.map_controller.get_world_map(self._current_map_id)
        if not world_map:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前地图信息未加载，无法导出",
                QMessageBox.StandardButton.Ok
            )
            return

        # 弹出保存文件对话框
        map_name = world_map.name
        default_filename = f"{map_name}_visible_points.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前显示点位",
            default_filename,
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        # 生成JSON
        json_str = generate_npc_export_json(
            self._current_map_id,
            map_name,
            world_map,
            points
        )

        # 保存文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info("导出当前显示点位成功: {}", file_path)
            QMessageBox.information(
                self,
                "导出成功",
                f"已成功导出 {len(points)} 个当前显示点位到:\n{file_path}",
                QMessageBox.StandardButton.Ok
            )
            self.ui.statusbar.showMessage(f"导出完成: {file_path}")
        except Exception as e:
            logger.error("导出当前显示点位失败: {}", str(e))
            QMessageBox.critical(
                self,
                "导出失败",
                f"保存文件时出错:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def _on_export_routes(self):
        """导出当前地图上所有已规划的路径

        导出每条路径包含完整点位信息和总距离，路径按顺序编号。
        """
        # 检查当前是否加载地图
        if not self._current_map_id:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前未加载任何地图，请先加载地图",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取所有已规划路径
        routes = self.map_scene.get_planned_routes()
        if not routes:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前地图没有规划任何路径，请先规划路径",
                QMessageBox.StandardButton.Ok
            )
            return

        # 获取世界地图信息
        world_map = self.map_controller.get_world_map(self._current_map_id)
        if not world_map:
            QMessageBox.warning(
                self,
                "无法导出",
                "当前地图信息未加载，无法导出",
                QMessageBox.StandardButton.Ok
            )
            return

        # 弹出保存文件对话框
        map_name = world_map.name
        default_filename = f"{map_name}_routes.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出所有已规划路径",
            default_filename,
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        # 生成JSON
        json_str = generate_route_export_json(
            self._current_map_id,
            map_name,
            world_map,
            routes
        )

        # 保存文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info("导出所有规划路径成功: {}", file_path)
            QMessageBox.information(
                self,
                "导出成功",
                f"已成功导出 {len(routes)} 条规划路径到:\n{file_path}",
                QMessageBox.StandardButton.Ok
            )
            self.ui.statusbar.showMessage(f"导出完成: {file_path}")
        except Exception as e:
            logger.error("导出规划路径失败: {}", str(e))
            QMessageBox.critical(
                self,
                "导出失败",
                f"保存文件时出错:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def _set_help_text(self):
        """设置使用帮助文本"""
        help_text = """<h3>操作说明</h3>
<b>=== 基本操作 ===</b><br>
• 左键拖动 → 平移地图<br>
• 右键拖动 → 框选点位（可多次框选）<br>
• Ctrl + 右键拖动 → 框选取消点位<br>
<br>
<b>=== 路径规划 ===</b><br>
• 框选多个点位后，点击其中一个点位自动设为起点<br>
• 点击「规划路径」→ 生成路径，自动清空选中，可继续规划下一条<br>
• 每条路径起点显示序号，序号与导出文件名对应<br>
• 点击「清空」→ 清空所有选择和所有已规划路径<br>
<br>
<b>=== 移除选中点 ===</b><br>
• 框选路径上要删除的点<br>
• 点击「移除选中」→ 删除选中点，自动将路径分割为多条<br>
• 分割后长度不足 2 个点的路径自动删除<br>
<br>
<b>=== 合并路径 ===</b><br>
• 必须框选：<i>所有需要合并路径</i> 的 <i>所有连接端点</i><br>
• 举例：合并 <code>a-c-d</code> 和 <code>d-f-e</code>，起点选 a → 至少需要框选 a（起点）和 d（连接点）<br>
• 通常情况下，直接框选要合并的路径的所有点即可，有多余点和其他不相连路径的点也没关系，不受影响 <br>
• 左键点击你想作为 <b>合并起点</b> 的端点（必须是路径端点）<br>
• 点击「合并路径」→ 从起点开始，自动合并所有相连路径<br>
• 合并规则：从起点出发，如果下一连接处端点已框选，则继续合并，遇到端点未框选时停止
"""
        self.ui.help_text.setHtml(help_text)

    def _on_merge_select_clicked(self):
        """从起点合并相连路径"""
        # 获取合并起点 = 用户当前点击选中显示信息的点
        start_point = self._selected_point
        selected_points = self.map_scene.get_selected_points()

        if not start_point:
            self.ui.point_info.setText("合并失败：\n请先点击选择一个端点作为合并起点")
            self.ui.statusbar.showMessage("合并失败")
            return

        selected_ids = {p.refresh_id for p in selected_points}
        if not selected_ids:
            self.ui.point_info.setText("合并失败：\n请至少框选要合并路径上的点")
            self.ui.statusbar.showMessage("合并失败")
            return

        # 获取所有已规划路径，收集包含至少一个选中点的候选路径
        all_routes = self.map_scene.get_planned_routes()
        candidates = [
            route for route in all_routes
            if any(p.refresh_id in selected_ids for p in route.points)
        ]

        if len(candidates) < 1:
            self.ui.point_info.setText("合并失败：\n没有找到包含选中点的已规划路径")
            self.ui.statusbar.showMessage("合并失败")
            return

        # 找到包含起点的路径，并检查起点是否是端点
        start_route = None
        start_is_head = False  # True: 起点在头部，False: 起点在尾部
        for route in candidates:
            if route.points[0].refresh_id == start_point.refresh_id:
                start_route = route
                start_is_head = True
                break
            if route.points[-1].refresh_id == start_point.refresh_id:
                start_route = route
                start_is_head = False
                break

        if not start_route:
            # 收集所有候选路径的端点，显示在信息框
            lines = ["合并失败：起点必须是候选路径的端点", ""]
            lines.append(f"当前起点: {start_point.display_name}")
            lines.append("")
            lines.append(f"候选路径({len(candidates)}条)端点:")
            for i, route in enumerate(candidates):
                head = route.points[0].display_name
                tail = route.points[-1].display_name
                lines.append(f"  路径{i+1}: {head} ↔ {tail}")
            self.ui.point_info.setText("\n".join(lines))
            self.ui.statusbar.showMessage("合并失败")
            logger.debug("合并失败: 起点 {} 不是任何候选路径的端点，候选路径数 {}",
                        start_point.display_name, len(candidates))
            return

        # 开始贪心合并
        merged_points: list[NpcPoint] = []
        # 收集所有被合并的路径
        to_remove: list[PlannedRoute] = [start_route]
        candidates.remove(start_route)
        merged_count = 1

        # 根据起点位置确定方向
        if start_is_head:
            # 起点在头部，正序添加
            merged_points.extend(start_route.points)
        else:
            # 起点在尾部，逆序添加
            merged_points.extend(reversed(start_route.points))

        current_point = merged_points[-1]

        # 循环查找下一个相连路径
        while candidates:
            # 检查当前端点是否被框选选中，不是则终止合并
            if current_point.refresh_id not in selected_ids:
                break

            found = False
            for route in candidates:
                # 检查当前点是否是这个路径的端点
                if route.points[0].refresh_id == current_point.refresh_id:
                    # 当前点在头部，正序添加（跳过重复起点）
                    merged_points.extend(route.points[1:])
                    current_point = route.points[-1]
                    to_remove.append(route)
                    candidates.remove(route)
                    merged_count += 1
                    found = True
                    break
                if route.points[-1].refresh_id == current_point.refresh_id:
                    # 当前点在尾部，逆序添加（跳过重复起点）
                    merged_points.extend(reversed(route.points[:-1]))
                    current_point = route.points[0]
                    to_remove.append(route)
                    candidates.remove(route)
                    merged_count += 1
                    found = True
                    break

            if not found:
                # 找不到相连的下一个路径，结束合并
                break

        # 删除所有被合并的原路径
        for route in to_remove:
            self.map_scene.remove_route(route)

        # 计算总距离
        world_map = self.map_controller.get_world_map(self._current_map_id)
        total_distance = 0.0
        if world_map:
            for i in range(len(merged_points) - 1):
                total_distance += self.map_scene._route_planner.distance(
                    merged_points[i], merged_points[i+1], world_map
                )

        # 添加合并后的新路径，使用起点原路径的颜色
        merged_color = start_route.color
        self.map_scene.add_planned_route(merged_points, total_distance, merged_color)

        # 清空选中状态，方便后续操作
        self._clear_route_selection()

        # 显示结果
        self.ui.statusbar.showMessage(
            f"合并完成: {merged_count} 条路径合并为 1 条，共 {len(merged_points)} 个点位，总距离 {total_distance:.1f}"
        )
        logger.info("路径合并完成: {} 条 → 1 条，{} 个点位，总距离 {:.1f}",
                    merged_count, len(merged_points), total_distance)

        # 在信息框显示合并后的路径详情
        self._show_route_info(merged_points, total_distance)

    def _on_remove_select_clicked(self):
        """删除选中点，断开路径为多条"""
        # 获取待删除点
        selected_points = self.map_scene.get_selected_points()
        to_delete_ids = {p.refresh_id for p in selected_points}

        if not to_delete_ids:
            self.ui.point_info.setText("删除失败：\n请先选择要删除的点")
            self.ui.statusbar.showMessage("删除失败")
            return

        # 获取所有已规划路径
        all_routes = self.map_scene.get_planned_routes().copy()
        world_map = self.map_controller.get_world_map(self._current_map_id)

        if not world_map:
            self.ui.point_info.setText("删除失败：\n当前地图未加载")
            self.ui.statusbar.showMessage("删除失败")
            return

        deleted_points_count = 0
        added_routes_count = 0
        original_routes_count = len(all_routes)

        # 处理每条路径：分割成多个片段
        for route in all_routes:
            # 检查路径是否包含要删除的点
            has_deleted = any(p.refresh_id in to_delete_ids for p in route.points)
            if not has_deleted:
                continue  # 不包含，跳过

            # 删除原路径
            self.map_scene.remove_route(route)
            deleted_points_count += sum(1 for p in route.points if p.refresh_id in to_delete_ids)

            # 分割路径为连续片段
            segments: list[list[NpcPoint]] = []
            current_segment: list[NpcPoint] = []

            for point in route.points:
                if point.refresh_id not in to_delete_ids:
                    current_segment.append(point)
                else:
                    # 遇到删除点，结束当前片段
                    if len(current_segment) >= 2:
                        segments.append(current_segment.copy())
                    current_segment.clear()
            # 添加最后一个片段
            if len(current_segment) >= 2:
                segments.append(current_segment)

            # 添加保留的片段
            for segment in segments:
                # 计算总距离
                total_distance = 0.0
                for i in range(len(segment) - 1):
                    total_distance += self.map_scene._route_planner.distance(
                        segment[i], segment[i+1], world_map
                    )
                self.map_scene.add_planned_route(segment, total_distance)
                added_routes_count += 1

        # 清空选中状态
        self._clear_route_selection()

        # 计算结果
        remaining_routes = len(self.map_scene.get_planned_routes())
        result_msg = (
            f"删除完成:\n"
            f"移除 {deleted_points_count} 个选中点\n"
            f"拆分出 {added_routes_count} 条新路径\n"
            f"剩余 {remaining_routes} 条路径"
        )

        self.ui.statusbar.showMessage(
            f"删除完成: 移除 {deleted_points_count} 点，新增 {added_routes_count} 条路径"
        )
        logger.info("删除选中点完成: 移除 {} 点，{} 条 → {} 条，新增 {} 条",
                    deleted_points_count, original_routes_count, remaining_routes, added_routes_count)

        self.ui.point_info.setText(result_msg)
