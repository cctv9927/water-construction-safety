#!/usr/bin/env python3
"""
水利工地传感器数据模拟器
在没有真实硬件的情况下，模拟发送传感器数据到 ThingsBoard MQTT Broker
用于测试整个数据链路（采集→转发→告警→处置闭环）

使用方法:
    python simulator.py --host localhost --port 1883 --interval 5
    python simulator.py --mode single --sensor-id sensor-001 --alert
    python simulator.py --stress --count 50  # 批量传感器压测
"""
import argparse
import json
import random
import time
import sys
import uuid
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ 缺少 paho-mqtt，请先安装: pip install paho-mqtt")
    sys.exit(1)


# ==================== 传感器类型定义 ====================

SENSOR_TYPES = {
    "water_level": {
        "name": "水位传感器",
        "unit": "m",
        "range": (0.0, 10.0),
        "warning_threshold": 8.0,
        "critical_threshold": 9.5,
        "normal_variation": 0.3,
    },
    "rainfall": {
        "name": "雨量传感器",
        "unit": "mm/h",
        "range": (0.0, 200.0),
        "warning_threshold": 100.0,
        "critical_threshold": 150.0,
        "normal_variation": 20.0,
    },
    "displacement": {
        "name": "位移传感器",
        "unit": "mm",
        "range": (0.0, 500.0),
        "warning_threshold": 200.0,
        "critical_threshold": 350.0,
        "normal_variation": 10.0,
    },
    "tilt": {
        "name": "倾斜传感器",
        "unit": "°",
        "range": (0.0, 30.0),
        "warning_threshold": 10.0,
        "critical_threshold": 20.0,
        "normal_variation": 1.0,
    },
    "vibration": {
        "name": "振动传感器",
        "unit": "mm/s",
        "range": (0.0, 50.0),
        "warning_threshold": 25.0,
        "critical_threshold": 40.0,
        "normal_variation": 5.0,
    },
}


def generate_value(sensor_type: str, prev_value: Optional[float] = None) -> Dict[str, Any]:
    """生成传感器读数"""
    cfg = SENSOR_TYPES.get(sensor_type, SENSOR_TYPES["water_level"])
    
    if prev_value is None:
        # 首次值：在正常范围内随机
        value = random.uniform(cfg["range"][0], cfg["range"][1] * 0.3)
    else:
        # 后续值：基于上一值随机漫步
        delta = random.uniform(-cfg["normal_variation"], cfg["normal_variation"])
        value = max(cfg["range"][0], min(cfg["range"][1], prev_value + delta))
    
    # 判断告警级别
    if value >= cfg["critical_threshold"]:
        level = "critical"
    elif value >= cfg["warning_threshold"]:
        level = "warning"
    else:
        level = "normal"
    
    return {
        "sensor_id": f"sensor-{uuid.uuid4().hex[:8]}",
        "type": sensor_type,
        "value": round(value, 3),
        "unit": cfg["unit"],
        "timestamp": datetime.now().isoformat() + "Z",
        "alert_level": level,
        "status": "online",
        "latitude": round(31.0 + random.uniform(-0.1, 0.1), 6),
        "longitude": round(121.0 + random.uniform(-0.1, 0.1), 6),
        "metadata": {
            "device_model": f"WL-{sensor_type.upper()}-v2",
            "firmware_version": "2.1.4",
            "battery_level": random.randint(60, 100),
        }
    }


def generate_stress_test(count: int) -> List[Dict[str, Any]]:
    """批量生成测试数据（压测用）"""
    results = []
    for i in range(count):
        sensor_type = random.choice(list(SENSOR_TYPES.keys()))
        data = generate_value(sensor_type)
        results.append(data)
    return results


def send_to_mqtt(data: Dict[str, Any], host: str, port: int, topic: str = "v1/devices/me/telemetry") -> bool:
    """发送数据到 ThingsBoard MQTT"""
    try:
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"✅ 连接 ThingsBoard 成功")
            else:
                print(f"❌ 连接失败，rc={rc}")
        
        client = mqtt.Client()
        client.on_connect = on_connect
        
        # ThingsBoard MQTT 无需认证（使用默认访问令牌）
        # 如果ThingsBoard启用了访问令牌检查，设置：
        # client.username_pw_set("YOUR_ACCESS_TOKEN")
        
        client.connect(host, port, keepalive=60)
        
        payload = json.dumps(data)
        result = client.publish(topic, payload)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            return True
        else:
            print(f"❌ 发送失败，rc={result.rc}")
            return False
            
    except Exception as e:
        print(f"❌ MQTT 错误: {e}")
        return False
    finally:
        try:
            client.disconnect()
        except:
            pass


def print_data(data: Dict[str, Any], use_colors: bool = True):
    """打印传感器数据（带颜色）"""
    level = data["alert_level"]
    type_name = SENSOR_TYPES[data["type"]]["name"]
    
    color_map = {
        "normal": "\033[92m",    # 绿色
        "warning": "\033[93m",   # 黄色
        "critical": "\033[91m",  # 红色
    }
    reset = "\033[0m"
    
    color = color_map.get(level, "") if use_colors else ""
    
    print(f"{color}[{level.upper():8}] {data['type']:12} {type_name:10} "
          f"值={data['value']:7.3f}{data['unit']} "
          f"设备={data['sensor_id']}{reset}")


def run_continuous(mode: str, host: str, port: int, interval: int, stress_count: int):
    """持续运行模拟"""
    print(f"\n{'='*60}")
    print(f"水利工地传感器模拟器")
    print(f"{'='*60}")
    print(f"模式: {mode}")
    print(f"MQTT: {host}:{port}")
    print(f"间隔: {interval}秒")
    print(f"{'='*60}\n")
    
    prev_values: Dict[str, float] = {}
    stress_datas: List[Dict] = []
    counter = 0
    
    try:
        while True:
            counter += 1
            
            if mode == "stress":
                # 批量压测模式
                stress_datas = generate_stress_test(stress_count)
                payload = json.dumps({"ts": int(time.time()*1000), "values": {}})
                for d in stress_datas:
                    payload["values"][d["sensor_id"]] = d["value"]
                
                print(f"[{counter}] 批量发送 {len(stress_datas)} 个传感器数据")
                send_to_mqtt(payload, host, port)
                
            elif mode == "single":
                # 单传感器模式
                sensor_type = "water_level"
                data = generate_value(sensor_type, prev_values.get(sensor_type))
                prev_values[sensor_type] = data["value"]
                
                print_data(data)
                
                # 同时发送到 MQTT（如果可用）
                if host != "localhost" or os.environ.get("TEST_MQTT", ""):
                    send_to_mqtt(data, host, port)
                    
            elif mode == "multi":
                # 多传感器模式
                for sensor_type in SENSOR_TYPES.keys():
                    data = generate_value(sensor_type, prev_values.get(sensor_type))
                    prev_values[sensor_type] = data["value"]
                    print_data(data)
                    
                    if host != "localhost":
                        send_to_mqtt(data, host, port)
                
                if host != "localhost":
                    # 批量发送
                    send_to_mqtt({"sensors": list(prev_values.keys())}, host, port)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 模拟器已停止")


def run_single(host: str, port: int, sensor_id: str, sensor_type: str, alert: bool):
    """单次发送模式"""
    print(f"发送单次传感器数据...")
    
    data = generate_value(sensor_type)
    data["sensor_id"] = sensor_id
    data["alert_level"] = "critical" if alert else "normal"
    
    print_data(data)
    
    if host != "localhost":
        success = send_to_mqtt(data, host, port)
        if success:
            print(f"✅ 发送成功")
        else:
            print(f"❌ 发送失败")
    else:
        print(f"(MQTT目标为localhost，仅打印数据)")


def main():
    parser = argparse.ArgumentParser(description="水利工地传感器模拟器")
    parser.add_argument("--host", default="localhost", help="ThingsBoard MQTT 主机")
    parser.add_argument("--port", type=int, default=1883, help="MQTT 端口")
    parser.add_argument("--mode", choices=["continuous", "single", "stress", "multi"], 
                       default="continuous", help="运行模式")
    parser.add_argument("--interval", type=int, default=5, help="发送间隔（秒）")
    parser.add_argument("--sensor-id", default="sensor-001", help="传感器ID（单次模式）")
    parser.add_argument("--sensor-type", default="water_level", 
                       choices=list(SENSOR_TYPES.keys()), help="传感器类型")
    parser.add_argument("--alert", action="store_true", help="强制发送告警级别数据")
    parser.add_argument("--stress", action="store_true", help="压测模式")
    parser.add_argument("--count", type=int, default=50, help="压测传感器数量")
    parser.add_argument("--stress-count", type=int, default=50, help="压测传感器数量")
    parser.add_argument("--list-types", action="store_true", help="列出所有传感器类型")
    
    args = parser.parse_args()
    
    if args.list_types:
        print("\n可用传感器类型：")
        for key, cfg in SENSOR_TYPES.items():
            print(f"  {key:15} {cfg['name']:12} 范围={cfg['range']} {cfg['unit']}  "
                  f"告警={cfg['warning_threshold']} 临界={cfg['critical_threshold']}")
        return
    
    if args.stress:
        args.mode = "stress"
    
    if args.mode == "single":
        run_single(args.host, args.port, args.sensor_id, args.sensor_type, args.alert)
    else:
        run_continuous(args.mode, args.host, args.port, args.interval, 
                      args.stress_count or args.count)


if __name__ == "__main__":
    main()
