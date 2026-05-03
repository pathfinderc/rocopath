"""
路径规划算法

提供可替换的路径规划算法实现：
- BaseRoutePlanner: 抽象基类，定义接口
- NearestNeighborPlanner: 最近邻贪心算法（快速，结果近似）
- ExactTspPlanner: 动态规划精确算法(Held-Karp)，全局最优解
- OrToolsTspPlanner: Google OR-Tools 启发式算法（工业级，支持大规模问题）
"""

from abc import ABC, abstractmethod
from math import sqrt
from typing import Union, TYPE_CHECKING
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from rocopath.models import NpcPoint, WorldMapInfo
from rocopath.core.npc_loader import NpcLoader

if TYPE_CHECKING:
    from rocopath.models.path_point import PathPoint

PlannablePoint = Union[NpcPoint, "PathPoint"]


class BaseRoutePlanner(ABC):
    """路径规划器抽象基类

    定义统一接口，便于后续替换更好的算法。
    """

    @abstractmethod
    def plan(
        self,
        points: list[PlannablePoint],
        start: PlannablePoint,
        world_map: WorldMapInfo
    ) -> list[PlannablePoint]:
        """规划路径，从起点出发访问所有点。

        Args:
            points: 所有需要访问的点位（已经去重）
            start: 指定的起点
            world_map: 世界地图信息（用于缩放距离计算）

        Returns:
            有序的点位列表，从起点开始，每个点恰好访问一次
        """
        raise NotImplementedError()

    def distance(
        self,
        a: PlannablePoint,
        b: PlannablePoint,
        world_map: WorldMapInfo
    ) -> float:
        """计算两点之间的3D欧氏距离（包含Z坐标，统一缩放）

        使用地图边长进行缩放，保证X/Y/Z尺度一致，避免数值溢出。
        """
        if a.area is None or b.area is None:
            dx = a.map_x - b.map_x
            dy = a.map_y - b.map_y
            return sqrt(dx * dx + dy * dy)

        dx_world = a.area.world_x - b.area.world_x
        dy_world = a.area.world_y - b.area.world_y
        dz_world = a.area.world_z - b.area.world_z

        scale = world_map.side_length / NpcLoader.MAP_PIXEL_SIZE
        dx = dx_world / scale
        dy = dy_world / scale
        dz = dz_world / scale

        return sqrt(dx * dx + dy * dy + dz * dz)

    def _two_opt_improve(
        self,
        path: list[PlannablePoint],
        world_map: WorldMapInfo
    ) -> list[PlannablePoint]:
        """2-opt 局部搜索：消除路径自交（路线重叠）

        在欧氏平面上，任何自交的路径都是次优的——解开交叉总能
        通过三角不等式缩短总距离。2-opt 反复检查每对不相邻的边，
        若交换后距离更短则执行翻转，直到不存在可改进的交叉。

        时间复杂度 O(n²·k)，k 为收敛迭代次数（通常 2-5 次）。
        对于已无交叉的路径仅验证一次即可退出。
        """
        n = len(path)
        if n <= 3:
            return path

        best = list(path)
        improved = True

        while improved:
            improved = False
            # 检查每对不相邻的边 (i,i+1) 和 (j,j+1)
            for i in range(n - 2):
                a = best[i]
                b = best[i + 1]
                ab = self.distance(a, b, world_map)

                for j in range(i + 2, n - 1):
                    c = best[j]
                    d = best[j + 1]
                    cd = self.distance(c, d, world_map)

                    # 翻转后新边: a→c 和 b→d
                    ac = self.distance(a, c, world_map)
                    bd = self.distance(b, d, world_map)

                    if ac + bd < ab + cd:
                        # 翻转 i+1 到 j 之间的路径段
                        best[i + 1:j + 1] = reversed(best[i + 1:j + 1])
                        improved = True

        return best


class NearestNeighborPlanner(BaseRoutePlanner):
    """最近邻路径规划算法

    算法逻辑：
    1. 从指定起点开始
    2. 当前点 → 找最近的未访问点 → 加入路径
    3. 重复直到所有点都被访问

    优点：
    - 实现简单，计算极快
    - 对于游戏导航来说结果足够可用
    - O(n²) 时间复杂度，几十个点完全没问题
    """

    def plan(
        self,
        points: list[PlannablePoint],
        start: PlannablePoint,
        world_map: WorldMapInfo
    ) -> list[PlannablePoint]:
        if len(points) <= 1:
            return list(points)

        # 确保起点在列表中
        if not any(p.point_id == start.point_id for p in points):
            points = [start] + list(points)

        # 使用 point_id (str) 跟踪未访问，因为 NpcPoint 不可哈希
        point_map = {p.point_id: p for p in points}
        unvisited_ids = set(point_map.keys())
        unvisited_ids.remove(start.point_id)

        path = [start]
        current = start

        while unvisited_ids:
            # 找离当前点最近的未访问点
            nearest: PlannablePoint | None = None
            min_dist = float('inf')
            for candidate_id in unvisited_ids:
                candidate = point_map[candidate_id]
                dist = self.distance(current, candidate, world_map)
                if dist < min_dist:
                    min_dist = dist
                    nearest = candidate

            if nearest is None:
                break

            path.append(nearest)
            unvisited_ids.remove(nearest.point_id)
            current = nearest

        return self._two_opt_improve(path, world_map)


class ExactTspPlanner(BaseRoutePlanner):
    """精确旅行商问题求解 - 动态规划Held-Karp算法

    找到**全局最短**路径，从起点出发访问所有点恰好一次。
    时间复杂度 O(n² 2ⁿ)，对于 n ≤ 16 非常快。
    n > 16 自动 fallback 到 NearestNeighbor 贪心算法。

    相比最近邻贪心算法，结果更优（总距离更短）。
    """

    # 阈值：超过这个点数自动fallback到贪心
    MAX_EXACT_POINTS = 16

    def __init__(self):
        self._fallback = NearestNeighborPlanner()

    def plan(
        self,
        points: list[PlannablePoint],
        start: PlannablePoint,
        world_map: WorldMapInfo
    ) -> list[PlannablePoint]:
        n = len(points)
        if n <= 1:
            return list(points)

        # 点数过多 → 自动fallback到最近邻贪心，避免长时间卡住
        if n > self.MAX_EXACT_POINTS:
            return self._fallback.plan(points, start, world_map)

        # 将起点放到索引0位置
        point_list = list(points)
        # 如果起点不在列表中，添加到开头
        if not any(p.point_id == start.point_id for p in point_list):
            point_list = [start] + point_list
            n = len(point_list)

        # 重新排列，让起点在索引0
        start_index = 0
        for i, p in enumerate(point_list):
            if p.point_id == start.point_id:
                start_index = i
                break
        if start_index != 0:
            # 交换到0位置
            point_list[0], point_list[start_index] = point_list[start_index], point_list[0]

        # 预计算距离矩阵
        dist: list[list[float]] = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dist[i][j] = self.distance(point_list[i], point_list[j], world_map)

        # DP优化：按mask大小分层，每层用列表存储，比字典快很多
        # dp[mask][u] = (最短距离, 前驱v)
        full_mask = (1 << n) - 1
        dp: list[list[float]] = [
            [float('inf')] * n
            for _ in range(1 << n)
        ]
        prev_node: list[list[int | None]] = [
            [None] * n
            for _ in range(1 << n)
        ]

        # 起点：只访问了0，在0位置
        dp[1 << 0][0] = 0.0

        # 遍历所有mask大小（从2开始，因为1已经处理）
        for mask_size in range(2, n + 1):
            # 遍历所有mask
            for mask in range(full_mask + 1):
                if not (mask & (1 << 0)):  # 必须包含起点
                    continue
                if bin(mask).count("1") != mask_size:
                    continue

                # 对于mask中每个终点u
                for u in range(n):
                    if not (mask & (1 << u)):
                        continue
                    if u == 0:
                        continue

                    # dp[mask][u] = min over v in mask, v != u of dp[mask ^ (1<<u)][v] + dist[v][u]
                    prev_mask = mask ^ (1 << u)
                    min_dist = float('inf')
                    best_v: int | None = None

                    for v in range(n):
                        if not (prev_mask & (1 << v)):
                            continue
                        if dp[prev_mask][v] == float('inf'):
                            continue
                        candidate_dist = dp[prev_mask][v] + dist[v][u]
                        if candidate_dist < min_dist:
                            min_dist = candidate_dist
                            best_v = v

                    if best_v is not None:
                        dp[mask][u] = min_dist
                        prev_node[mask][u] = best_v

        # 找到访问所有点（mask全1）的最短终点
        min_total = float('inf')
        last_u: int | None = None

        for u in range(1, n):
            if dp[full_mask][u] < min_total:
                min_total = dp[full_mask][u]
                last_u = u

        # 回溯重建路径
        path_indices: list[int] = []
        current = last_u
        mask = full_mask

        while current is not None:
            path_indices.append(current)
            p = prev_node[mask][current]
            mask = mask ^ (1 << current)
            current = p

        # 反转得到从起点开始的路径
        path_indices.reverse()
        # 转换回点位列表
        result = [point_list[i] for i in path_indices]

        return result


class OrToolsTspPlanner(BaseRoutePlanner):
    """Google OR-Tools TSP 路径规划算法

    工业级启发式算法，使用引导式局部搜索 (GUIDED_LOCAL_SEARCH)
    解质量高，支持大规模点集。

    OR-Tools 默认是闭合回路模型（起点=终点），本算法会自动去掉末尾的重复起点，
    得到真正的开放路径。
    """

    def __init__(self, time_limit_sec: int = 3):
        """
        Args:
            time_limit_sec: OR-Tools 求解时间限制（秒），30-50 点 3 秒足够
        """
        self.time_limit_sec = time_limit_sec

    def plan(
        self,
        points: list[PlannablePoint],
        start: PlannablePoint,
        world_map: WorldMapInfo
    ) -> list[PlannablePoint]:
        n = len(points)
        if n <= 1:
            return list(points)

        # 将起点放到索引0位置
        point_list = list(points)
        # 如果起点不在列表中，添加到开头
        if not any(p.point_id == start.point_id for p in point_list):
            point_list = [start] + point_list
            n = len(point_list)

        # 重新排列，让起点在索引0
        start_index = 0
        for i, p in enumerate(point_list):
            if p.point_id == start.point_id:
                start_index = i
                break
        if start_index != 0:
            point_list[0], point_list[start_index] = point_list[start_index], point_list[0]

        # 预计算距离矩阵（整数化，OR-Tools 要求整数成本）
        # 优化：只计算 i<j，利用对称性节省一半计算量
        dist: list[list[int]] = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = self.distance(point_list[i], point_list[j], world_map)
                dist[i][j] = dist[j][i] = int(d * 1e6)

        # 创建 OR-Tools 路由模型
        manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # 1辆车，起点固定在索引0
        routing = pywrapcp.RoutingModel(manager)

        # 注册距离回调
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist[from_node][to_node]

        transit_callback = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback)

        # 配置搜索参数
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = self.time_limit_sec

        # 求解
        solution = routing.SolveWithParameters(search_params)
        if not solution:
            # 求解失败 fallback 到最近邻
            return NearestNeighborPlanner().plan(points, start, world_map)

        # 提取回路顺序（第一个点是起点，最后一个点也是起点）
        path_indices: list[int] = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            path_indices.append(node)
            index = solution.Value(routing.NextVar(index))

        # 关键修正：OR-Tools 默认是闭合回路，去掉末尾的重复起点得到开放路径
        if path_indices and path_indices[0] == path_indices[-1]:
            path_indices.pop()

        result = [point_list[i] for i in path_indices]

        return self._two_opt_improve(result, world_map)
