"""
通信链路展示模块
GCS-OBC-FCU拓扑图与MAVLink数据流模拟
"""

import json
import time
import random
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    HEARTBEAT = 0
    GPS_RAW_INT = 1
    ATTITUDE = 2
    GLOBAL_POSITION_INT = 3
    MISSION_ITEM_INT = 4
    COMMAND_LONG = 5
    MISSION_COUNT = 6
    MISSION_ACK = 7
    STATUSTEXT = 8
    SYS_STATUS = 9


class LinkType(Enum):
    GCS_TO_OBC = "GCS->OBC"
    OBC_TO_FCU = "OBC->FCU"
    FCU_TO_GCS = "FCU->GCS"
    BACKUP_LINK = "Backup"


@dataclass
class MAVLinkMessage:
    msg_type: MessageType
    timestamp: float
    system_id: int
    component_id: int
    sequence: int
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.msg_type.name,
            "timestamp": self.timestamp,
            "system_id": self.system_id,
            "component_id": self.component_id,
            "sequence": self.sequence,
            "payload": self.payload
        }


@dataclass
class LinkStatus:
    link_type: LinkType
    is_active: bool = True
    latency_ms: float = 0.0
    packet_loss_rate: float = 0.0
    last_update: float = field(default_factory=time.time)


class CommunicationTopology:
    """通信拓扑管理"""

    def __init__(self):
        self.links: Dict[str, LinkStatus] = {}
        self.message_log: List[MAVLinkMessage] = []
        self.max_log_size = 1000
        self._init_topology()

    def _init_topology(self) -> None:
        self.add_link("GCS", "OBC", LinkType.GCS_TO_OBC)
        self.add_link("OBC", "FCU", LinkType.OBC_TO_FCU)
        self.add_link("FCU", "GCS", LinkType.FCU_TO_GCS)
        self.add_link("GCS", "FCU", LinkType.BACKUP_LINK)

    def add_link(self, from_node: str, to_node: str, link_type: LinkType) -> None:
        self.links[f"{from_node}->{to_node}"] = LinkStatus(link_type)

    def get_topology_for_visualization(self) -> Dict[str, Any]:
        nodes = [
            {"id": "GCS", "label": "地面控制站", "type": "GCS"},
            {"id": "OBC", "label": "机载计算机", "type": "OBC"},
            {"id": "FCU", "label": "飞行控制器", "type": "FCU"},
        ]
        links = []
        for lid, status in self.links.items():
            f, t = lid.split("->")
            links.append({"source": f, "target": t, "type": status.link_type.value, "active": status.is_active})
        return {"nodes": nodes, "links": links}


class MAVLinkSimulator:
    """MAVLink数据流模拟器"""

    def __init__(self, topology: CommunicationTopology):
        self.topology = topology
        self.is_running = False
        self.callbacks: List[Callable[[MAVLinkMessage], None]] = []
        self._thread: Optional[threading.Thread] = None
        self._seq = 0
        self._templates = self._init_templates()

    def _init_templates(self) -> Dict[MessageType, Dict[str, Any]]:
        return {
            MessageType.HEARTBEAT: {"type": 1, "autopilot": 3, "base_mode": 81, "system_status": 4},
            MessageType.GPS_RAW_INT: {"lat": 320642000, "lon": 1187115000, "alt": 100000, "fix_type": 3},
            MessageType.ATTITUDE: {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            MessageType.GLOBAL_POSITION_INT: {
                "lat": 320642000, "lon": 1187115000, "alt": 100000,
                "relative_alt": 50000, "vx": 0, "vy": 0, "vz": 0
            },
            MessageType.SYS_STATUS: {"voltage_battery": 12000, "battery_remaining": 80, "CPU_load": 20}
        }

    def start(self) -> None:
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._loop)
            self._thread.daemon = True
            self._thread.start()

    def stop(self) -> None:
        self.is_running = False

    def add_callback(self, cb: Callable[[MAVLinkMessage], None]) -> None:
        self.callbacks.append(cb)

    def _loop(self) -> None:
        while self.is_running:
            self._generate()
            time.sleep(0.5)

    def _generate(self) -> None:
        types = [MessageType.HEARTBEAT, MessageType.GPS_RAW_INT,
                 MessageType.ATTITUDE, MessageType.GLOBAL_POSITION_INT, MessageType.SYS_STATUS]
        msg_type = random.choice(types)
        tpl = self._templates[msg_type].copy()

        if msg_type == MessageType.GPS_RAW_INT:
            tpl["lat"] += random.randint(-100, 100)
            tpl["lon"] += random.randint(-100, 100)
        elif msg_type == MessageType.ATTITUDE:
            tpl["roll"] = random.uniform(-0.1, 0.1)
            tpl["pitch"] = random.uniform(-0.1, 0.1)
            tpl["yaw"] = random.uniform(0, 360)

        self._seq = (self._seq + 1) % 256
        msg = MAVLinkMessage(msg_type, time.time(), 1, 1, self._seq, tpl)

        self.topology.message_log.append(msg)
        if len(self.topology.message_log) > self.topology.max_log_size:
            self.topology.message_log.pop(0)

        for cb in self.callbacks:
            try:
                cb(msg)
            except Exception:
                pass

    def get_message_log_json(self, limit: int = 100) -> str:
        msgs = [m.to_dict() for m in self.topology.message_log[-limit:]]
        return json.dumps(msgs, indent=2)


def demo_communication():
    """演示通信链路"""
    print("=" * 50)
    print("通信链路演示")
    print("=" * 50)
    topology = CommunicationTopology()
    sim = MAVLinkSimulator(topology)

    counts = {}
    def cb(msg):
        counts[msg.msg_type.name] = counts.get(msg.msg_type.name, 0) + 1

    sim.add_callback(cb)
    sim.start()
    time.sleep(3)
    sim.stop()

    print("消息统计:")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    demo_communication()
