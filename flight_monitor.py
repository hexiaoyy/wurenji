"""
飞行监控模块 - 南京科技职业学院
实时显示无人机状态、位置、高度等信息
"""

import time
import random
import json
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class FlightMode(Enum):
    MANUAL = "手动模式"
    STABILIZE = "增稳模式"
    ALT_HOLD = "高度保持"
    POS_HOLD = "位置保持"
    MISSION = "任务模式"
    RTL = "返航模式"
    LAND = "着陆模式"


class FlightStatus(Enum):
    DISARMED = "未解锁"
    ARMED = "已解锁"
    TAKING_OFF = "起飞中"
    FLYING = "飞行中"
    LANDING = "着陆中"
    EMERGENCY = "紧急状态"


@dataclass
class DroneState:
    timestamp: float = field(default_factory=time.time)
    latitude: float = 32.0642
    longitude: float = 118.7115
    altitude: float = 0.0
    relative_altitude: float = 0.0
    ground_speed: float = 0.0
    air_speed: float = 0.0
    heading: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    battery_voltage: float = 12.0
    battery_current: float = 0.0
    battery_remaining: int = 100
    flight_mode: FlightMode = FlightMode.STABILIZE
    flight_status: FlightStatus = FlightStatus.DISARMED
    gps_fix_type: int = 3
    gps_satellites: int = 12
    cpu_load: int = 0
    memory_usage: int = 0
    vibration: float = 0.0


class FlightMonitor:
    """飞行监控类"""

    def __init__(self):
        self.current_state = DroneState()
        self.state_history: List[DroneState] = []
        self.max_history = 1000
        self.is_monitoring = False
        self.callbacks: List[Callable[[DroneState], None]] = []
        self._thread: Optional[threading.Thread] = None

    def start_monitoring(self) -> None:
        if not self.is_monitoring:
            self.is_monitoring = True
            self._thread = threading.Thread(target=self._monitor_loop)
            self._thread.daemon = True
            self._thread.start()

    def stop_monitoring(self) -> None:
        self.is_monitoring = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def add_state_callback(self, callback: Callable[[DroneState], None]) -> None:
        self.callbacks.append(callback)

    def _monitor_loop(self) -> None:
        while self.is_monitoring:
            self._update_state()
            for cb in self.callbacks:
                try:
                    cb(self.current_state)
                except Exception:
                    pass
            time.sleep(0.1)

    def _update_state(self) -> None:
        s = self.current_state
        s.timestamp = time.time()

        if s.flight_status in [FlightStatus.FLYING, FlightStatus.TAKING_OFF]:
            s.latitude += random.uniform(-0.00001, 0.00001)
            s.longitude += random.uniform(-0.00001, 0.00001)
            s.altitude = max(0, s.altitude + random.uniform(-0.5, 0.5))
            s.relative_altitude = max(0, s.relative_altitude + random.uniform(-0.5, 0.5))
            s.battery_remaining = max(0, s.battery_remaining - 0.01)

        s.roll = random.uniform(-5, 5)
        s.pitch = random.uniform(-5, 5)
        s.yaw = (s.yaw + random.uniform(-1, 1)) % 360
        s.ground_speed = random.uniform(0, 10) if s.flight_status == FlightStatus.FLYING else 0
        s.cpu_load = random.randint(15, 45)

        self.state_history.append(DroneState(**s.__dict__))
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)

    def arm(self) -> None:
        self.current_state.flight_status = FlightStatus.ARMED

    def disarm(self) -> None:
        self.current_state.flight_status = FlightStatus.DISARMED

    def take_off(self, altitude: float) -> None:
        self.current_state.flight_status = FlightStatus.TAKING_OFF
        self.current_state.flight_mode = FlightMode.ALT_HOLD
        self.current_state.altitude = altitude
        self.current_state.relative_altitude = altitude
        time.sleep(0.5)
        self.current_state.flight_status = FlightStatus.FLYING

    def land(self) -> None:
        self.current_state.flight_status = FlightStatus.LANDING
        self.current_state.flight_mode = FlightMode.LAND
        while self.current_state.relative_altitude > 0:
            self.current_state.relative_altitude = max(0, self.current_state.relative_altitude - 1)
            time.sleep(0.05)
        self.current_state.flight_status = FlightStatus.DISARMED

    def set_flight_mode(self, mode: FlightMode) -> None:
        self.current_state.flight_mode = mode

    def get_state_json(self) -> str:
        s = self.current_state
        return json.dumps({
            "timestamp": s.timestamp,
            "position": {
                "latitude": s.latitude,
                "longitude": s.longitude,
                "altitude": s.altitude,
                "relative_altitude": s.relative_altitude
            },
            "speed": {"ground_speed": s.ground_speed, "air_speed": s.air_speed, "heading": s.heading},
            "attitude": {"roll": s.roll, "pitch": s.pitch, "yaw": s.yaw},
            "battery": {
                "voltage": s.battery_voltage,
                "current": s.battery_current,
                "remaining": s.battery_remaining
            },
            "flight_mode": s.flight_mode.value,
            "flight_status": s.flight_status.value,
            "gps": {"fix_type": s.gps_fix_type, "satellites": s.gps_satellites},
            "system": {"cpu_load": s.cpu_load, "memory_usage": s.memory_usage, "vibration": s.vibration}
        }, indent=2)

    def get_telemetry_data(self) -> Dict[str, Any]:
        s = self.current_state
        return {
            "lat": s.latitude, "lon": s.longitude, "alt": s.altitude,
            "relative_alt": s.relative_altitude, "speed": s.ground_speed,
            "heading": s.heading, "battery": s.battery_remaining,
            "status": s.flight_status.value
        }


def demo_flight_monitor():
    """演示飞行监控"""
    print("=" * 50)
    print("飞行监控演示 - 南京科技职业学院")
    print("=" * 50)

    monitor = FlightMonitor()
    monitor.current_state.latitude = 32.0642
    monitor.current_state.longitude = 118.7115
    monitor.start_monitoring()

    def cb(state):
        print(f"\r状态: {state.flight_status.value} | 高度: {state.relative_altitude:.1f}m | "
              f"电池: {state.battery_remaining:.0f}%", end="")

    monitor.add_state_callback(cb)

    time.sleep(1)
    print("\n\n解锁...")
    monitor.arm()
    time.sleep(1)

    print("\n起飞到50米...")
    monitor.take_off(50)
    time.sleep(3)

    print("\n着陆...")
    monitor.land()
    time.sleep(1)

    monitor.stop_monitoring()
    print("\n完成")


if __name__ == "__main__":
    demo_flight_monitor()
