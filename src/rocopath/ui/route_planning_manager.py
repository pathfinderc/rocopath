"""
路径规划管理器

统一管理路径规划相关的UI交互和业务逻辑：
- 6 个按钮交互（全选/清空/重置/规划/合并/删除）
- MapView 交互信号（框选、点选）
- 业务逻辑（合并路径、删除选中点）
- UI 状态更新（按钮启用、标签文字）
- 点位信息显示

保持主窗口代码简洁，遵循与 FilterPanel / ExportImportPanel 相同的组件化模式。
"""

from collections.abc import Callable
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QMessageBox
from loguru import logger

from rocopath.ui.map_scene import MapScene, PlannedRoute
from rocopath.ui.npc_point_item import NpcPointItem
from rocopath.core.map_controller import MapController
from rocopath.models import NpcPoint


class RoutePlanningManager:
    """路径规划管理器"""

    def __init__(
        self,
        get_map_scene: Callable[[], MapScene],
        get_map_controller: Callable[[], MapController],
        get_current_map_id: Callable[[], str],
        get_selected_point: Callable[[], NpcPoint | None],
        set_selected_point: Callable[[NpcPoint | None], None],
        show_point_info: Callable[[str], None],
        show_status: Callable[[str], None],
        set_select_num_text: Callable[[str], None],
        set_start_status_text: Callable[[str], None],
        set_clear_select_enabled: Callable[[bool], None],
        set_reset_all_enabled: Callable[[bool], None],
        set_plan_route_enabled: Callable[[bool], None],
    ):
        self._get_map_scene = get_map_scene
        self._get_map_controller = get_map_controller
        self._get_current_map_id = get_current_map_id
        self._get_selected_point = get_selected_point
        self._set_selected_point = set_selected_point
        self._show_point_info = show_point_info
        self._show_status = show_status
        self._set_select_num_text = set_select_num_text
        self._set_start_status_text = set_start_status_text
        self._set_clear_select_enabled = set_clear_select_enabled
        self._set_reset_all_enabled = set_reset_all_enabled
        self._set_plan_route_enabled = set_plan_route_enabled

    # ===== 按钮处理方法 =====

    def on_select_all(self) -> None:
        """全选当前显示的所有点位"""
        self._get_map_scene().select_all()
        self._update_route_ui_state()
        logger.debug("全选完成，共 {} 个点位", self._get_map_scene().get_selected_count())

    def on_clear_selection(self) -> None:
        """清空选中状态，但保留已规划路径"""
        self._clear_route_selection()
        logger.debug("清空选中状态完成")
        self._show_status("已清空选中状态")

    def on_reset_all(self) -> None:
        """清空所有路径选择和已规划路径"""
        self._clear_route_selection_and_routes()
        logger.debug("清空路径选择和所有已规划路径")

    def on_plan_route(self) -> None:
        """点击规划路径按钮"""
        map_id = self._get_current_map_id()
        world_map = self._get_map_controller().get_world_map(map_id)
        if world_map is None:
            self._show_status("无法获取地图信息，规划失败")
            return

        planned_path, total_distance = self._get_map_scene().plan_route(world_map)
        if not planned_path:
            return

        self._show_status(
            f"规划完成: 共 {len(planned_path)} 个点位，总距离 {total_distance:.1f}"
        )

        self._show_route_info(planned_path, total_distance)

        logger.debug("路径规划完成: {} 个点位，总距离 {:.1f}",
                    len(planned_path), total_distance)

        self._clear_route_selection()

    def on_merge_selected(self) -> None:
        """从起点合并相连路径"""
        start_point = self._get_selected_point()
        if not start_point:
            self._show_point_info("合并失败：\n请先点击选择一个端点作为合并起点")
            self._show_status("合并失败")
            return

        selected_points = self._get_map_scene().get_selected_points()
        selected_ids = {p.refresh_id for p in selected_points}
        if not selected_ids:
            self._show_point_info("合并失败：\n请至少框选要合并路径上的点")
            self._show_status("合并失败")
            return

        all_routes = self._get_map_scene().get_planned_routes()
        candidates = [
            route for route in all_routes
            if any(p.refresh_id in selected_ids for p in route.points)
        ]

        if len(candidates) < 1:
            self._show_point_info("合并失败：\n没有找到包含选中点的已规划路径")
            self._show_status("合并失败")
            return

        start_route = None
        start_is_head = False
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
            lines = ["合并失败：起点必须是候选路径的端点", ""]
            lines.append(f"当前起点: {start_point.display_name}")
            lines.append("")
            lines.append(f"候选路径({len(candidates)}条)端点:")
            for i, route in enumerate(candidates):
                head = route.points[0].display_name
                tail = route.points[-1].display_name
                lines.append(f"  路径{i+1}: {head} ↔ {tail}")
            self._show_point_info("\n".join(lines))
            self._show_status("合并失败")
            logger.debug("合并失败: 起点 {} 不是任何候选路径的端点，候选路径数 {}",
                        start_point.display_name, len(candidates))
            return

        merged_points: list[NpcPoint] = []
        to_remove: list[PlannedRoute] = [start_route]
        candidates.remove(start_route)
        merged_count = 1

        if start_is_head:
            merged_points.extend(start_route.points)
        else:
            merged_points.extend(reversed(start_route.points))

        current_point = merged_points[-1]

        while candidates:
            if current_point.refresh_id not in selected_ids:
                break

            found = False
            for route in candidates:
                if route.points[0].refresh_id == current_point.refresh_id:
                    merged_points.extend(route.points[1:])
                    current_point = route.points[-1]
                    to_remove.append(route)
                    candidates.remove(route)
                    merged_count += 1
                    found = True
                    break
                if route.points[-1].refresh_id == current_point.refresh_id:
                    merged_points.extend(reversed(route.points[:-1]))
                    current_point = route.points[0]
                    to_remove.append(route)
                    candidates.remove(route)
                    merged_count += 1
                    found = True
                    break

            if not found:
                break

        for route in to_remove:
            self._get_map_scene().remove_route(route)

        map_id = self._get_current_map_id()
        world_map = self._get_map_controller().get_world_map(map_id)
        total_distance = 0.0
        if world_map:
            for i in range(len(merged_points) - 1):
                total_distance += self._get_map_scene()._route_planner.distance(
                    merged_points[i], merged_points[i+1], world_map
                )

        merged_color = start_route.color
        self._get_map_scene().add_planned_route(merged_points, total_distance, merged_color)

        self._clear_route_selection()

        self._show_status(
            f"合并完成: {merged_count} 条路径合并为 1 条，共 {len(merged_points)} 个点位，总距离 {total_distance:.1f}"
        )
        logger.info("路径合并完成: {} 条 → 1 条，{} 个点位，总距离 {:.1f}",
                    merged_count, len(merged_points), total_distance)

        self._show_route_info(merged_points, total_distance)

    def on_remove_selected(self) -> None:
        """删除选中点，断开路径为多条"""
        selected_points = self._get_map_scene().get_selected_points()
        to_delete_ids = {p.refresh_id for p in selected_points}

        if not to_delete_ids:
            self._show_point_info("删除失败：\n请先选择要删除的点")
            self._show_status("删除失败")
            return

        all_routes = self._get_map_scene().get_planned_routes().copy()
        map_id = self._get_current_map_id()
        world_map = self._get_map_controller().get_world_map(map_id)

        if not world_map:
            self._show_point_info("删除失败：\n当前地图未加载")
            self._show_status("删除失败")
            return

        deleted_points_count = 0
        added_routes_count = 0
        original_routes_count = len(all_routes)

        for route in all_routes:
            has_deleted = any(p.refresh_id in to_delete_ids for p in route.points)
            if not has_deleted:
                continue

            self._get_map_scene().remove_route(route)
            deleted_points_count += sum(1 for p in route.points if p.refresh_id in to_delete_ids)

            segments: list[list[NpcPoint]] = []
            current_segment: list[NpcPoint] = []

            for point in route.points:
                if point.refresh_id not in to_delete_ids:
                    current_segment.append(point)
                else:
                    if len(current_segment) >= 2:
                        segments.append(current_segment.copy())
                    current_segment.clear()

            if len(current_segment) >= 2:
                segments.append(current_segment)

            for segment in segments:
                total_distance = 0.0
                for i in range(len(segment) - 1):
                    total_distance += self._get_map_scene()._route_planner.distance(
                        segment[i], segment[i+1], world_map
                    )
                self._get_map_scene().add_planned_route(segment, total_distance)
                added_routes_count += 1

        self._clear_route_selection()

        remaining_routes = len(self._get_map_scene().get_planned_routes())
        result_msg = (
            f"删除完成:\n"
            f"移除 {deleted_points_count} 个选中点\n"
            f"拆分出 {added_routes_count} 条新路径\n"
            f"剩余 {remaining_routes} 条路径"
        )

        self._show_status(
            f"删除完成: 移除 {deleted_points_count} 点，新增 {added_routes_count} 条路径"
        )
        logger.info("删除选中点完成: 移除 {} 点，{} 条 → {} 条，新增 {} 条",
                    deleted_points_count, original_routes_count, remaining_routes, added_routes_count)

        self._show_point_info(result_msg)

    # ===== MapView 交互处理 =====

    def handle_box_selection(self, rect: QRectF, modifiers: Qt.KeyboardModifier) -> None:
        """处理框选完成：添加或移除矩形内的点位"""
        self._get_map_scene().handle_box_selection(rect, modifiers)
        self._update_route_ui_state()
        count = self._get_map_scene().get_selected_count()
        remove_mode = modifiers & Qt.KeyboardModifier.ControlModifier
        logger.debug("框选完成: remove_mode={}, 现在共 {} 个选中",
                    remove_mode, count)

    def handle_point_click(self, item: NpcPointItem) -> None:
        """处理点选：toggle 选中状态"""
        self._get_map_scene().handle_point_click(item)
        self._update_route_ui_state()

    def on_point_selected(self, refresh_id: int) -> None:
        """点位被点击：显示详情并自动设为路径起点"""
        map_id = self._get_current_map_id()
        point = self._get_map_controller().get_point_by_refresh_id(map_id, refresh_id)
        if point is None:
            logger.warning("找不到点位: refresh_id={}", refresh_id)
            return

        self._get_map_scene().set_selected(refresh_id)
        self._set_selected_point(point)
        self._show_point_info_detail(point)

        if self._get_map_scene().is_selected(refresh_id):
            self._set_route_start(point)
            self._show_status(f"起点已设置: {point.display_name}")

    # ===== 内部辅助方法 =====

    def _update_route_ui_state(self) -> None:
        """根据当前状态更新UI控件启用/禁用和显示文字"""
        has_selection = self._get_map_scene().get_selected_count() > 0
        has_routes = self._get_map_scene().has_planned_routes()

        self._set_select_num_text(f"选中点位: {self._get_map_scene().get_selected_count()}")

        start_point = self._get_map_scene().get_route_start()
        if start_point:
            self._set_start_status_text(f"起点: {start_point.display_name}")
        else:
            self._set_start_status_text("起点: 未选择")

        self._set_clear_select_enabled(has_selection)
        self._set_reset_all_enabled(has_selection or has_routes)

        can_plan = (
            self._get_map_scene().get_selected_count() >= 2 and
            start_point is not None
        )
        self._set_plan_route_enabled(can_plan)

    def _clear_route_selection(self) -> None:
        """清空所有路径选择状态（保留已规划路径）"""
        self._get_map_scene().clear_route_selection()
        self._update_route_ui_state()

    def _clear_route_selection_and_routes(self) -> None:
        """清空所有路径选择和已规划路径"""
        self._get_map_scene().clear_route_selection_and_routes()
        self._update_route_ui_state()

    def _set_route_start(self, point: NpcPoint) -> None:
        """设置路径起点"""
        self._get_map_scene().set_route_start(point)
        self._update_route_ui_state()

    def _show_point_info_detail(self, point: NpcPoint) -> None:
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
        self._show_point_info(info)

    def _show_route_info(self, points: list[NpcPoint], total_distance: float) -> None:
        """在信息框显示路径详情"""
        if not points:
            return

        lines = [f"规划路径: {len(points)} 个点位", f"总距离: {total_distance:.1f}", ""]
        for i, point in enumerate(points, 1):
            lines.append(f"{i}. {point.display_name}")

        info = "\n".join(lines)
        self._show_point_info(info)
