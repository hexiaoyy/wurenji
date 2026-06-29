"""
无人机飞行规划系统 - Streamlit版
坐标: 南京科技职业学院 (32.0642°N, 118.7115°E)
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import time
import random
from shapely.geometry import Polygon, LineString, Point
from coordinate_converter import CoordinateConverter

st.set_page_config(
    page_title="无人机飞行规划系统 - 南京科技职业学院",
    page_icon="🛸",
    layout="wide"
)

CENTER_LAT = 32.0642
CENTER_LON = 118.7115
CAMPUS_NAME = "南京科技职业学院"

if 'obstacles' not in st.session_state:
    st.session_state.obstacles = [
        {"name": "教学楼A", "height": 45.0,
         "coords": [[32.0650, 118.7110], [32.0655, 118.7110],
                    [32.0655, 118.7118], [32.0650, 118.7118]]},
        {"name": "实验楼B", "height": 60.0,
         "coords": [[32.0638, 118.7120], [32.0642, 118.7120],
                    [32.0642, 118.7128], [32.0638, 118.7128]]}
    ]
if 'flight_altitude' not in st.session_state:
    st.session_state.flight_altitude = 100
if 'safety_radius' not in st.session_state:
    st.session_state.safety_radius = 10
if 'mavlink_running' not in st.session_state:
    st.session_state.mavlink_running = False
if 'monitor_running' not in st.session_state:
    st.session_state.monitor_running = False

converter = CoordinateConverter()

st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
    .stApp { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
    h1, h2, h3 { color: #00d4ff !important; }
    .metric-card {
        background: rgba(0,212,255,0.1);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(0,212,255,0.3);
    }
    .metric-value { font-size: 32px; font-weight: bold; color: #00d4ff; }
    .metric-label { font-size: 12px; color: #888; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🛸 无人机飞行规划系统")
st.caption(f"📍 {CAMPUS_NAME} | 坐标: {CENTER_LAT}°N, {CENTER_LON}°E")

tab1, tab2, tab3 = st.tabs(["🗺️ 地图", "📡 通信链路", "🛩️ 飞行监控"])

# ========== 地图标签页 ==========
with tab1:
    col1, col2 = st.columns([1, 2.5])

    with col1:
        st.subheader("3.1 坐标转换")
        c1, c2 = st.columns(2)
        with c1:
            inp_lon = st.number_input("经度", value=CENTER_LON, step=0.000001, format="%.6f")
        with c2:
            inp_lat = st.number_input("纬度", value=CENTER_LAT, step=0.000001, format="%.6f")

        bc1, bc2 = st.columns(2)
        if bc1.button("WGS-84 → GCJ-02", use_container_width=True):
            glon, glat = converter.wgs84_to_gcj02(inp_lon, inp_lat)
            st.success(f"GCJ-02: ({glon:.6f}, {glat:.6f})")
        if bc2.button("GCJ-02 → WGS-84", use_container_width=True):
            wlon, wlat = converter.gcj02_to_wgs84(inp_lon, inp_lat)
            st.success(f"WGS-84: ({wlon:.6f}, {wlat:.6f})")

        st.divider()
        st.subheader("3.2 障碍物设置")
        obs_name = st.text_input("障碍物名称", value=f"障碍物{len(st.session_state.obstacles)+1}")
        obs_height = st.number_input("障碍物高度 (米)", value=50, min_value=0)

        st.info("💡 在右侧地图上点击添加多边形顶点")

        if 'drawing_points' not in st.session_state:
            st.session_state.drawing_points = []

        ob1, ob2, ob3 = st.columns(3)
        if ob1.button("闭合多边形", use_container_width=True):
            if len(st.session_state.drawing_points) >= 3:
                st.session_state.obstacles.append({
                    "name": obs_name,
                    "height": obs_height,
                    "coords": st.session_state.drawing_points.copy()
                })
                st.session_state.drawing_points = []
                st.success(f"障碍物 '{obs_name}' 已添加")
                st.rerun()
            else:
                st.warning("至少需要3个顶点")
        if ob2.button("撤销点", use_container_width=True):
            if st.session_state.drawing_points:
                st.session_state.drawing_points.pop()
                st.rerun()
        if ob3.button("清空障碍", use_container_width=True):
            st.session_state.obstacles = []
            st.session_state.drawing_points = []
            st.rerun()

        st.divider()
        st.subheader("障碍物列表")
        for i, obs in enumerate(st.session_state.obstacles):
            with st.expander(f"📐 {obs['name']} ({obs['height']}m)"):
                st.write(f"顶点数: {len(obs['coords'])}")

        st.divider()
        st.subheader("3.3 飞行参数")
        st.session_state.flight_altitude = st.slider("飞行高度 (米)", 20, 400, st.session_state.flight_altitude)
        st.session_state.safety_radius = st.slider("安全半径 (米)", 5, 50, st.session_state.safety_radius)

        st.divider()
        st.subheader("3.4 路径规划")
        sc1, sc2 = st.columns(2)
        with sc1:
            start_lat = st.number_input("起点纬度", value=CENTER_LAT, step=0.000001, format="%.6f")
            start_lon = st.number_input("起点经度", value=CENTER_LON, step=0.000001, format="%.6f")
        with sc2:
            end_lat = st.number_input("终点纬度", value=CENTER_LAT + 0.002, step=0.000001, format="%.6f")
            end_lon = st.number_input("终点经度", value=CENTER_LON + 0.003, step=0.000001, format="%.6f")

        rp1, rp2 = st.columns(2)
        if rp1.button("✈️ 规划飞越航线", use_container_width=True):
            st.session_state.direct_route = [[start_lat, start_lon], [end_lat, end_lon]]
            st.success("飞越航线已规划")
        if rp2.button("↩️ 规划绕飞航线", use_container_width=True):
            mlat = (start_lat + end_lat) / 2
            mlon = (start_lon + end_lon) / 2 + 0.0008
            st.session_state.bypass_route = [[start_lat, start_lon], [mlat, mlon], [end_lat, end_lon]]
            st.success("绕飞航线已规划")

    with col2:
        m = folium.Map(location=[CENTER_LAT, CENTER_LON], zoom_start=17,
                       tiles='https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
                       attr='© 高德地图')

        folium.Marker([CENTER_LAT, CENTER_LON],
                      popup=f"{CAMPUS_NAME}<br>起始点<br>({CENTER_LAT}, {CENTER_LON})",
                      icon=folium.Icon(color='green', icon='play', prefix='glyphicon')).add_to(m)

        for obs in st.session_state.obstacles:
            folium.Polygon(obs["coords"], color='red', weight=2,
                           fill=True, fillColor='red', fillOpacity=0.3,
                           popup=f"{obs['name']}<br>高度: {obs['height']}m").add_to(m)

        if 'direct_route' in st.session_state:
            folium.PolyLine(st.session_state.direct_route, color='#00d4ff',
                            weight=3, opacity=0.8).add_to(m)
            for i, p in enumerate(st.session_state.direct_route):
                folium.CircleMarker(p, radius=6, color='#00d4ff',
                                    fill=True, fillColor='#00d4ff', fillOpacity=0.7).add_to(m)
        if 'bypass_route' in st.session_state:
            folium.PolyLine(st.session_state.bypass_route, color='#ffaa00',
                            weight=3, opacity=0.8, dashArray='10,5').add_to(m)
            for i, p in enumerate(st.session_state.bypass_route):
                folium.CircleMarker(p, radius=6, color='#ffaa00',
                                    fill=True, fillColor='#ffaa00', fillOpacity=0.7).add_to(m)

        output = st_folium(m, width="100%", height=600)

        if output.get('last_clicked'):
            lat = output['last_clicked']['lat']
            lng = output['last_clicked']['lng']
            st.info(f"点击位置: {lat:.6f}, {lng:.6f}")

# ========== 通信链路标签页 ==========
with tab2:
    st.subheader("3.4.1 GCS-OBC-FCU 通信拓扑图")

    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:20px;padding:30px;background:rgba(0,0,0,0.3);border-radius:15px;">
        <div style="padding:30px 40px;background:#e94560;border-radius:15px;text-align:center;min-width:140px;">
            <div style="font-size:40px;">📡</div>
            <div style="font-weight:bold;font-size:18px;margin-top:8px;">GCS</div>
            <div style="font-size:12px;opacity:0.8;margin-top:4px;">地面控制站</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;">
            <div style="font-size:12px;color:#888;">15ms / WiFi</div>
            <div style="width:80px;height:2px;background:linear-gradient(90deg,#00d4ff,#00ff00);margin:8px 0;"></div>
        </div>
        <div style="padding:30px 40px;background:#0f3460;border:1px solid #00d4ff;border-radius:15px;text-align:center;min-width:140px;">
            <div style="font-size:40px;">💻</div>
            <div style="font-weight:bold;font-size:18px;margin-top:8px;">OBC</div>
            <div style="font-size:12px;opacity:0.8;margin-top:4px;">机载计算机</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;">
            <div style="font-size:12px;color:#888;">5ms / UART</div>
            <div style="width:80px;height:2px;background:linear-gradient(90deg,#00d4ff,#00ff00);margin:8px 0;"></div>
        </div>
        <div style="padding:30px 40px;background:#533483;border-radius:15px;text-align:center;min-width:140px;">
            <div style="font-size:40px;">🎮</div>
            <div style="font-weight:bold;font-size:18px;margin-top:8px;">FCU</div>
            <div style="font-size:12px;opacity:0.8;margin-top:4px;">飞行控制器</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("### 链路状态")
        st.success("✅ GCS → OBC 正常 (延迟: 15ms, 丢包: 0.1%)")
        st.success("✅ OBC → FCU 正常 (延迟: 5ms, 丢包: 0.0%)")
        st.warning("⚠️ 备份链路 待机")
    with sc2:
        st.markdown("### 数据速率")
        st.info("📤 上行速率: 1.2 Mbps")
        st.info("📥 下行速率: 2.5 Mbps")
        st.info("📡 MAVLink帧率: 50 Hz")

    st.divider()
    st.subheader("3.4.2 MAVLink 报文数据流")

    mc1, mc2 = st.columns(2)
    with mc1:
        if st.button("▶️ 启动MAVLink模拟", use_container_width=True):
            st.session_state.mavlink_running = True
    with mc2:
        if st.button("⏹️ 停止模拟", use_container_width=True):
            st.session_state.mavlink_running = False

    if 'msg_log' not in st.session_state:
        st.session_state.msg_log = []
    if 'msg_counts' not in st.session_state:
        st.session_state.msg_counts = {}

    if st.session_state.mavlink_running:
        types = ['HEARTBEAT', 'GPS_RAW_INT', 'ATTITUDE', 'GLOBAL_POSITION_INT', 'SYS_STATUS']
        msg_type = random.choice(types)
        now = time.strftime('%H:%M:%S') + f".{random.randint(0,999):03d}"
        content_map = {
            'HEARTBEAT': 'type=Quadrotor autopilot=PX4 status=ACTIVE',
            'GPS_RAW_INT': f'lat={int(320642000+random.randint(-100,100))} lon={int(1187115000+random.randint(-100,100))} fix=3D',
            'ATTITUDE': f'roll={random.uniform(-5,5):.2f} pitch={random.uniform(-5,5):.2f} yaw={random.randint(0,360)}',
            'GLOBAL_POSITION_INT': f'vx={random.randint(0,500)} vy={random.randint(0,500)} vz={random.randint(-100,100)}',
            'SYS_STATUS': f'load={random.randint(15,45)}% battery={random.randint(70,100)}%'
        }
        st.session_state.msg_log.insert(0, f"[{now}] {msg_type}: {content_map[msg_type]}")
        st.session_state.msg_counts[msg_type] = st.session_state.msg_counts.get(msg_type, 0) + 1
        if len(st.session_state.msg_log) > 50:
            st.session_state.msg_log = st.session_state.msg_log[:50]
        time.sleep(0.3)
        st.rerun()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("总消息", len(st.session_state.msg_log))
    c2.metric("HEARTBEAT", st.session_state.msg_counts.get('HEARTBEAT', 0))
    c3.metric("GPS_RAW", st.session_state.msg_counts.get('GPS_RAW_INT', 0))
    c4.metric("ATTITUDE", st.session_state.msg_counts.get('ATTITUDE', 0))
    c5.metric("SYS_STATUS", st.session_state.msg_counts.get('SYS_STATUS', 0))

    st.text_area("报文日志", value="\n".join(st.session_state.msg_log[:20]) if st.session_state.msg_log else "等待MAVLink数据流启动...",
                 height=300, font_size=12)

# ========== 飞行监控标签页 ==========
with tab3:
    st.subheader("3.3 飞行监控")

    if 'drone_state' not in st.session_state:
        st.session_state.drone_state = {
            'lat': CENTER_LAT, 'lon': CENTER_LON, 'alt': 0.0,
            'speed': 0.0, 'battery': 100, 'satellites': 12,
            'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'heading': 0.0,
            'voltage': 12.6, 'current': 0.0, 'cpu': 15, 'mem': 30,
            'status': '未解锁', 'mode': '高度保持'
        }

    st.markdown("### 实时遥测")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    ds = st.session_state.drone_state
    m1.markdown(f'<div class="metric-card"><div class="metric-value">{ds["lat"]:.6f}</div><div class="metric-label">纬度</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><div class="metric-value">{ds["lon"]:.6f}</div><div class="metric-label">经度</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><div class="metric-value">{ds["alt"]:.1f}m</div><div class="metric-label">高度</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><div class="metric-value">{ds["speed"]:.1f}m/s</div><div class="metric-label">地速</div></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="metric-card"><div class="metric-value">{ds["battery"]:.0f}%</div><div class="metric-label">电池</div></div>', unsafe_allow_html=True)
    m6.markdown(f'<div class="metric-card"><div class="metric-value">{ds["satellites"]}</div><div class="metric-label">GPS卫星</div></div>', unsafe_allow_html=True)

    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 姿态信息")
        st.metric("横滚 Roll", f"{ds['roll']:.2f}°")
        st.metric("俯仰 Pitch", f"{ds['pitch']:.2f}°")
        st.metric("偏航 Yaw", f"{ds['yaw']:.0f}°")
        st.metric("航向 Heading", f"{ds['heading']:.0f}°")

    with col2:
        st.markdown("### 电池状态")
        st.metric("电量", f"{ds['battery']:.0f}%")
        st.metric("电压", f"{ds['voltage']:.2f} V")
        st.metric("电流", f"{ds['current']:.1f} A")
        if ds['current'] > 0:
            est = (ds['battery'] * ds['voltage'] * 0.8) / (ds['current'] * ds['voltage']) * 60
            st.metric("预计剩余", f"{est:.0f} min")
        else:
            st.metric("预计剩余", "-- min")

    with col3:
        st.markdown("### 系统状态")
        st.metric("CPU负载", f"{ds['cpu']}%")
        st.metric("内存使用", f"{ds['mem']}%")
        st.metric("飞行模式", ds['mode'])
        status_color = "🟢" if ds['status'] in ['已解锁', '飞行中'] else "🔴"
        st.metric("飞行状态", f"{status_color} {ds['status']}")

    with col4:
        st.markdown("### GPS信息")
        st.success("3D定位")
        st.metric("卫星数量", ds['satellites'])
        st.metric("水平精度", "1.2 m")
        st.metric("垂直精度", "1.8 m")

    st.divider()
    st.markdown("### 飞行控制")
    bc1, bc2, bc3, bc4, bc5 = st.columns(5)
    if bc1.button("🔓 解锁", use_container_width=True):
        st.session_state.drone_state['status'] = '已解锁'
        st.rerun()
    if bc2.button("🔒 上锁", use_container_width=True):
        st.session_state.drone_state['status'] = '未解锁'
        st.session_state.drone_state['alt'] = 0
        st.session_state.drone_state['speed'] = 0
        st.rerun()
    if bc3.button("🚀 起飞", use_container_width=True):
        st.session_state.drone_state['status'] = '起飞中'
        st.session_state.drone_state['alt'] = 50
        st.session_state.drone_state['speed'] = 3
        st.session_state.drone_state['current'] = 18
        st.rerun()
    if bc4.button("🪂 着陆", use_container_width=True):
        st.session_state.drone_state['status'] = '已着陆'
        st.session_state.drone_state['alt'] = 0
        st.session_state.drone_state['speed'] = 0
        st.session_state.drone_state['current'] = 2
        st.rerun()
    if bc5.button("↩️ 返航", use_container_width=True):
        st.session_state.drone_state['status'] = '返航中'
        st.rerun()

    mode = st.select_slider("飞行模式",
                            options=["手动模式", "增稳模式", "高度保持", "位置保持", "任务模式", "返航模式", "着陆模式"],
                            value=st.session_state.drone_state['mode'])
    if mode != st.session_state.drone_state['mode']:
        st.session_state.drone_state['mode'] = mode
        st.rerun()

    if st.button("▶️ 启动实时监控", use_container_width=True):
        st.session_state.monitor_running = True
        st.rerun()
    if st.button("⏹️ 停止监控", use_container_width=True):
        st.session_state.monitor_running = False
        st.rerun()

    if st.session_state.monitor_running:
        d = st.session_state.drone_state
        if d['status'] in ['飞行中', '起飞中', '返航中']:
            d['lat'] += random.uniform(-0.00002, 0.00002)
            d['lon'] += random.uniform(-0.00002, 0.00002)
            d['alt'] = max(0, d['alt'] + random.uniform(-0.5, 0.5))
            d['battery'] = max(0, d['battery'] - 0.02)
            d['voltage'] = 10.8 + (d['battery'] / 100) * 1.8
        d['roll'] = random.uniform(-5, 5)
        d['pitch'] = random.uniform(-5, 5)
        d['yaw'] = random.randint(0, 360)
        d['heading'] = random.randint(0, 360)
        d['satellites'] = random.randint(10, 15)
        d['cpu'] = random.randint(15, 45)
        d['mem'] = random.randint(30, 50)
        time.sleep(0.5)
        st.rerun()
