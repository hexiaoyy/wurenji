"""
无人机飞行规划系统 - 主程序
坐标: 南京科技职业学院 (32.0642°N, 118.7115°E)
"""

import os
import json
from flask import Flask, render_template, request, jsonify
from coordinate_converter import CoordinateConverter, NJUST_CENTER
from map_display import CampusMap, create_campus_map
from route_planning import RoutePlanner, PolygonSelector, save_route_to_json
from communication_link import CommunicationTopology, MAVLinkSimulator
from flight_monitor import FlightMonitor, FlightMode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'drone_njtech_2024'

converter = CoordinateConverter()
route_planner = RoutePlanner(flight_altitude=100.0, safety_radius=10.0)
polygon_selector = PolygonSelector()
topology = CommunicationTopology()
mavlink_simulator = MAVLinkSimulator(topology)
flight_monitor = FlightMonitor()
campus_map: CampusMap = None

CENTER_LAT = 32.0642
CENTER_LON = 118.7115


def init_system():
    """初始化系统 - 南京科技职业学院"""
    global campus_map

    campus_map = create_campus_map(
        lat=CENTER_LAT,
        lon=CENTER_LON,
        zoom=17
    )

    # 示例障碍物
    obs1 = [
        (32.0650, 118.7110),
        (32.0655, 118.7110),
        (32.0655, 118.7118),
        (32.0650, 118.7118)
    ]
    campus_map.add_obstacle_polygon(obs1, height=45.0, name="教学楼A")

    obs2 = [
        (32.0638, 118.7120),
        (32.0642, 118.7120),
        (32.0642, 118.7128),
        (32.0638, 118.7128)
    ]
    campus_map.add_obstacle_polygon(obs2, height=60.0, name="实验楼B")

    # 初始化飞行监控
    flight_monitor.current_state.latitude = CENTER_LAT
    flight_monitor.current_state.longitude = CENTER_LON
    flight_monitor.current_state.gps_fix_type = 3
    flight_monitor.current_state.gps_satellites = 12


# ============ 路由 ============

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "location": "南京科技职业学院",
        "center": {"lat": CENTER_LAT, "lon": CENTER_LON}
    })


@app.route('/api/health')
def api_health():
    return jsonify({"status": "success", "message": "系统运行正常", "version": "1.0.0"})


@app.route('/')
def index():
    return render_template('index.html')


# 坐标转换
@app.route('/api/convert/wgs84_to_gcj02', methods=['POST'])
def api_wgs84_to_gcj02():
    data = request.json
    lon, lat = data.get('lon'), data.get('lat')
    if lon is None or lat is None:
        return jsonify({"status": "error", "message": "缺少参数"})
    glon, glat = converter.wgs84_to_gcj02(lon, lat)
    return jsonify({"status": "success", "wgs84": {"lon": lon, "lat": lat}, "gcj02": {"lon": glon, "lat": glat}})


@app.route('/api/convert/gcj02_to_wgs84', methods=['POST'])
def api_gcj02_to_wgs84():
    data = request.json
    lon, lat = data.get('lon'), data.get('lat')
    if lon is None or lat is None:
        return jsonify({"status": "error", "message": "缺少参数"})
    wlon, wlat = converter.gcj02_to_wgs84(lon, lat)
    return jsonify({"status": "success", "gcj02": {"lon": lon, "lat": lat}, "wgs84": {"lon": wlon, "lat": wlat}})


# 障碍物
@app.route('/api/obstacle/add_point', methods=['POST'])
def api_obstacle_add_point():
    data = request.json
    lat, lon = data.get('lat'), data.get('lon')
    if lat is None or lon is None:
        return jsonify({"status": "error"})
    polygon_selector.add_point(lat, lon)
    return jsonify({"status": "success", "point_count": len(polygon_selector.points)})


@app.route('/api/obstacle/remove_last', methods=['POST'])
def api_obstacle_remove_last():
    p = polygon_selector.remove_last_point()
    return jsonify({"status": "success" if p else "error", "point_count": len(polygon_selector.points)})


@app.route('/api/obstacle/close', methods=['POST'])
def api_obstacle_close():
    data = request.json
    height = data.get('height', 50)
    name = data.get('name', '障碍物')
    poly = polygon_selector.close_polygon()
    if not poly:
        return jsonify({"status": "error", "message": "至少3个顶点"})
    coords = [(lat, lon) for lat, lon in polygon_selector.points]
    campus_map.add_obstacle_polygon(coords, height=height, name=name)
    route_planner.add_obstacle(poly, height=height, name=name)
    campus_map.export_obstacles_json('static/obstacles.json')
    polygon_selector.clear()
    return jsonify({"status": "success", "name": name, "height": height})


@app.route('/api/obstacle/list')
def api_obstacle_list():
    return jsonify({
        "status": "success",
        "obstacles": [{"name": o["name"], "height": o["height"]} for o in campus_map.obstacles]
    })


@app.route('/api/obstacle/clear', methods=['POST'])
def api_obstacle_clear():
    polygon_selector.clear()
    route_planner.obstacles = []
    campus_map.obstacles = []
    return jsonify({"status": "success"})


# 飞行参数
@app.route('/api/flight/parameters', methods=['GET', 'POST'])
def api_flight_params():
    if request.method == 'POST':
        data = request.json
        if 'altitude' in data:
            route_planner.flight_altitude = data['altitude']
        if 'safety_radius' in data:
            route_planner.safety_radius = data['safety_radius']
    return jsonify({
        "flight_altitude": route_planner.flight_altitude,
        "safety_radius": route_planner.safety_radius
    })


# 路径规划
@app.route('/api/route/plan_direct', methods=['POST'])
def api_plan_direct():
    data = request.json
    start = tuple(data.get('start', []))
    end = tuple(data.get('end', []))
    if not start or not end:
        return jsonify({"status": "error"})
    route_planner.set_start_end(start, end)
    route = route_planner.plan_direct_route()
    safe, warns = route_planner.validate_route(route, route_planner.flight_altitude)
    return jsonify({"status": "success", "route": route, "is_safe": safe, "warnings": warns})


@app.route('/api/route/plan_bypass', methods=['POST'])
def api_plan_bypass():
    data = request.json
    obs_idx = data.get('obstacle_index', 0)
    side = data.get('side', 'left')
    start = tuple(data.get('start', []))
    end = tuple(data.get('end', []))
    if start and end:
        route_planner.set_start_end(start, end)
    route = route_planner.plan_bypass_route(obs_idx, side)
    return jsonify({"status": "success", "route": route})


# 通信链路
@app.route('/api/communication/topology')
def api_topology():
    return jsonify({"status": "success", "topology": topology.get_topology_for_visualization()})


@app.route('/api/mavlink/messages')
def api_mavlink_messages():
    limit = request.args.get('limit', 100, type=int)
    return jsonify({"status": "success", "messages": json.loads(mavlink_simulator.get_message_log_json(limit))})


@app.route('/api/mavlink/start', methods=['POST'])
def api_mavlink_start():
    if not mavlink_simulator.is_running:
        mavlink_simulator.start()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "已在运行"})


@app.route('/api/mavlink/stop', methods=['POST'])
def api_mavlink_stop():
    if mavlink_simulator.is_running:
        mavlink_simulator.stop()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "未运行"})


# 飞行监控
@app.route('/api/monitor/state')
def api_monitor_state():
    return jsonify({"status": "success", "state": json.loads(flight_monitor.get_state_json())})


@app.route('/api/monitor/telemetry')
def api_monitor_telemetry():
    return jsonify({"status": "success", "telemetry": flight_monitor.get_telemetry_data()})


@app.route('/api/monitor/start', methods=['POST'])
def api_monitor_start():
    if not flight_monitor.is_monitoring:
        flight_monitor.start_monitoring()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})


@app.route('/api/monitor/stop', methods=['POST'])
def api_monitor_stop():
    if flight_monitor.is_monitoring:
        flight_monitor.stop_monitoring()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})


@app.route('/api/monitor/arm', methods=['POST'])
def api_arm():
    flight_monitor.arm()
    return jsonify({"status": "success"})


@app.route('/api/monitor/disarm', methods=['POST'])
def api_disarm():
    flight_monitor.disarm()
    return jsonify({"status": "success"})


@app.route('/api/monitor/takeoff', methods=['POST'])
def api_takeoff():
    alt = request.json.get('altitude', 50)
    flight_monitor.take_off(alt)
    return jsonify({"status": "success"})


@app.route('/api/monitor/land', methods=['POST'])
def api_land():
    flight_monitor.land()
    return jsonify({"status": "success"})


# 启动时初始化
init_system()


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    print("=" * 50)
    print("无人机飞行规划系统")
    print("地点: 南京科技职业学院")
    print(f"坐标: {CENTER_LAT}°N, {CENTER_LON}°E")
    print("=" * 50)
    print("访问地址: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5000)
