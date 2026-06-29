"""
飞行路径规划模块
支持飞越和绕飞两种模式 - 南京科技职业学院
"""

import math
import json
from typing import List, Tuple, Optional, Dict, Any
from shapely.geometry import Polygon, LineString, Point


class RoutePlanner:
    """路径规划类"""

    def __init__(self, flight_altitude: float = 100.0, safety_radius: float = 10.0):
        self.flight_altitude = flight_altitude
        self.safety_radius = safety_radius
        self.obstacles: List[Dict[str, Any]] = []
        self.start_point: Optional[Point] = None
        self.end_point: Optional[Point] = None

    def set_flight_parameters(self, altitude: float, safety_radius: float) -> None:
        self.flight_altitude = altitude
        self.safety_radius = safety_radius

    def add_obstacle(self, polygon: Polygon, height: float, name: str = "障碍物") -> None:
        self.obstacles.append({
            "polygon": polygon,
            "height": height,
            "name": name
        })

    def set_start_end(self, start: Tuple[float, float], end: Tuple[float, float]) -> None:
        self.start_point = Point(start)
        self.end_point = Point(end)

    def check_collision(self, point: Tuple[float, float], altitude: float) -> bool:
        p = Point(point)
        for obstacle in self.obstacles:
            if p.distance(obstacle["polygon"]) < self.safety_radius:
                if altitude < obstacle["height"] + self.safety_radius:
                    return True
        return False

    def check_line_collision(self, start: Tuple[float, float],
                            end: Tuple[float, float], altitude: float) -> bool:
        line = LineString([start, end])
        for obstacle in self.obstacles:
            obs_polygon = obstacle["polygon"]
            obs_height = obstacle["height"]
            if line.intersects(obs_polygon) or line.distance(obs_polygon) < self.safety_radius:
                if altitude < obs_height + self.safety_radius:
                    return True
        return False

    def plan_direct_route(self) -> List[Tuple[float, float]]:
        if not self.start_point or not self.end_point:
            return []
        return [(self.start_point.y, self.start_point.x),
                (self.end_point.y, self.end_point.x)]

    def plan_bypass_route(self, obstacle_index: int, side: str = "left") -> List[Tuple[float, float]]:
        if obstacle_index < 0 or obstacle_index >= len(self.obstacles):
            return []

        obstacle = self.obstacles[obstacle_index]
        bounds = obstacle["polygon"].bounds
        min_lon, min_lat, max_lon, max_lat = bounds
        offset = 0.0003

        if side == "left":
            bypass = [
                (min_lat - offset, min_lon - offset),
                (max_lat + offset, min_lon - offset),
                (max_lat + offset, max_lon + offset),
                (min_lat - offset, max_lon + offset),
            ]
        else:
            bypass = [
                (min_lat - offset, max_lon + offset),
                (max_lat + offset, max_lon + offset),
                (max_lat + offset, min_lon - offset),
                (min_lat - offset, min_lon - offset),
            ]

        route = []
        if self.start_point:
            route.append((self.start_point.y, self.start_point.x))
        route.extend(bypass)
        if self.end_point:
            route.append((self.end_point.y, self.end_point.x))
        return route

    def find_safe_altitude(self, start: Tuple[float, float], end: Tuple[float, float]) -> float:
        max_h = 0.0
        line = LineString([start, end])
        for obstacle in self.obstacles:
            if line.intersects(obstacle["polygon"]):
                max_h = max(max_h, obstacle["height"])
        return max_h + self.safety_radius + 20.0

    def validate_route(self, route: List[Tuple[float, float]],
                      altitude: float) -> Tuple[bool, List[str]]:
        warnings = []
        is_safe = True
        for i in range(len(route) - 1):
            if self.check_line_collision(route[i], route[i + 1], altitude):
                warnings.append(f"航线段 {i+1} 与障碍物冲突")
                is_safe = False
        return is_safe, warnings


class PolygonSelector:
    """多边形选择器"""

    def __init__(self):
        self.points: List[Tuple[float, float]] = []
        self.is_closed: bool = False

    def add_point(self, lat: float, lon: float) -> None:
        self.points.append((lat, lon))

    def remove_last_point(self) -> Optional[Tuple[float, float]]:
        if self.points:
            return self.points.pop()
        return None

    def close_polygon(self) -> Optional[Polygon]:
        if len(self.points) >= 3:
            self.is_closed = True
            return Polygon(self.points)
        return None

    def get_polygon(self) -> Optional[Polygon]:
        if len(self.points) >= 3:
            return Polygon(self.points)
        return None

    def clear(self) -> None:
        self.points = []
        self.is_closed = False


def save_route_to_json(route: List[Tuple[float, float]], filename: str,
                      altitude: float, route_type: str) -> None:
    data = {
        "route_type": route_type,
        "altitude": altitude,
        "waypoints": [{"lat": lat, "lon": lon} for lat, lon in route]
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def demo_route_planning():
    """演示路径规划 - 南京科技职业学院"""
    planner = RoutePlanner(flight_altitude=100.0, safety_radius=10.0)

    start = (32.0642, 118.7115)
    end = (32.0660, 118.7140)
    planner.set_start_end(start, end)

    obs1 = Polygon([
        (32.0652, 118.7110), (32.0657, 118.7110),
        (32.0657, 118.7118), (32.0652, 118.7118)
    ])
    planner.add_obstacle(obs1, height=45.0, name="教学楼A")

    obs2 = Polygon([
        (32.0638, 118.7120), (32.0642, 118.7120),
        (32.0642, 118.7128), (32.0638, 118.7128)
    ])
    planner.add_obstacle(obs2, height=60.0, name="实验楼B")

    direct = planner.plan_direct_route()
    print("飞越航线:", direct)

    safe, warns = planner.validate_route(direct, 100.0)
    print(f"安全验证: {'通过' if safe else '未通过'}")

    bypass = planner.plan_bypass_route(0, "left")
    print("绕飞航线(左):", bypass)

    save_route_to_json(direct, "route_direct.json", 100.0, "direct")
    save_route_to_json(bypass, "route_bypass.json", 100.0, "bypass")
    print("航线已保存")


if __name__ == "__main__":
    demo_route_planning()
