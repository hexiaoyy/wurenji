"""
OpenStreetMap地图显示模块
坐标: 南京科技职业学院 (32.0642°N, 118.7115°E)
"""

import folium
import json
from typing import List, Tuple, Optional, Dict, Any
from shapely.geometry import Polygon, LineString, Point
from coordinate_converter import CoordinateConverter, NJUST_CENTER


class CampusMap:
    """校园地图类"""

    def __init__(self, center_lat: float, center_lon: float, zoom: int = 16):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom = zoom
        self.map: Optional[folium.Map] = None
        self.obstacles: List[Dict[str, Any]] = []
        self.start_point: Optional[Tuple[float, float]] = None
        self.waypoints: List[Tuple[float, float]] = []
        self.flight_route: Optional[LineString] = None

    def create_map(self) -> folium.Map:
        self.map = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom,
            tiles='OpenStreetMap'
        )
        return self.map

    def add_start_point(self, lat: float, lon: float, name: str = "起始点",
                        icon_color: str = "green") -> None:
        self.start_point = (lat, lon)
        folium.Marker(
            location=[lat, lon],
            popup=name,
            icon=folium.Icon(color=icon_color, icon='play', prefix='glyphicon'),
            tooltip=name
        ).add_to(self.map)
        folium.Circle(
            location=[lat, lon],
            radius=5,
            color=icon_color,
            fill=True,
            fillColor=icon_color,
            fillOpacity=0.4
        ).add_to(self.map)

    def add_obstacle_polygon(self, coordinates: List[Tuple[float, float]],
                            height: float, name: str = "障碍物") -> Dict[str, Any]:
        obstacle = {
            "name": name,
            "coordinates": coordinates,
            "height": height,
            "polygon": Polygon(coordinates)
        }
        self.obstacles.append(obstacle)
        folium.Polygon(
            locations=coordinates,
            color='red',
            weight=2,
            fill=True,
            fillColor='red',
            fillOpacity=0.3,
            popup=f"{name}<br>高度: {height}m",
            tooltip=f"{name} ({height}m)"
        ).add_to(self.map)
        return obstacle

    def set_obstacle_height(self, obstacle_index: int, height: float) -> None:
        if 0 <= obstacle_index < len(self.obstacles):
            self.obstacles[obstacle_index]["height"] = height

    def add_waypoint(self, lat: float, lon: float, order: int) -> None:
        self.waypoints.append((lat, lon))
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.7,
            popup=f"航点 {order}",
            tooltip=f"WP{order}"
        ).add_to(self.map)

    def draw_flight_route(self, route_points: List[Tuple[float, float]],
                         color: str = "blue") -> None:
        if len(route_points) < 2:
            return
        self.flight_route = LineString(route_points)
        folium.PolyLine(
            locations=route_points,
            weight=3,
            color=color,
            opacity=0.8,
            popup="飞行航线"
        ).add_to(self.map)

    def save_map(self, filename: str) -> None:
        if self.map:
            self.map.save(filename)

    def export_obstacles_json(self, filename: str) -> None:
        data = {
            "obstacles": [
                {
                    "name": obs["name"],
                    "coordinates": obs["coordinates"],
                    "height": obs["height"]
                }
                for obs in self.obstacles
            ]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_obstacles_json(self) -> str:
        data = {
            "obstacles": [
                {
                    "name": obs["name"],
                    "coordinates": [[lat, lon] for lat, lon in obs["coordinates"]],
                    "height": obs["height"]
                }
                for obs in self.obstacles
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


def create_campus_map(lat: float = 32.0642, lon: float = 118.7115,
                      zoom: int = 16) -> CampusMap:
    """创建校园地图 - 南京科技职业学院"""
    campus = CampusMap(lat, lon, zoom)
    campus.create_map()
    campus.add_start_point(lat, lon, "飞行起始点")
    return campus


def demo_map():
    """演示地图功能 - 南京科技职业学院"""
    campus = create_campus_map()

    # 示例障碍物
    obs1 = [
        (32.0652, 118.7110),
        (32.0657, 118.7110),
        (32.0657, 118.7118),
        (32.0652, 118.7118)
    ]
    campus.add_obstacle_polygon(obs1, height=45.0, name="教学楼A")

    obs2 = [
        (32.0638, 118.7120),
        (32.0642, 118.7120),
        (32.0642, 118.7128),
        (32.0638, 118.7128)
    ]
    campus.add_obstacle_polygon(obs2, height=60.0, name="实验楼B")

    # 航点
    waypoints = [
        (32.0644, 118.7117),
        (32.0648, 118.7122),
        (32.0652, 118.7126),
        (32.0656, 118.7130)
    ]
    for i, (lat, lon) in enumerate(waypoints):
        campus.add_waypoint(lat, lon, i + 1)
    campus.draw_flight_route(waypoints)

    campus.save_map('campus_map_njtech.html')
    campus.export_obstacles_json('obstacles.json')
    print("地图已保存到 campus_map_njtech.html")
    print("障碍物数据已保存到 obstacles.json")
    return campus


if __name__ == "__main__":
    demo_map()
