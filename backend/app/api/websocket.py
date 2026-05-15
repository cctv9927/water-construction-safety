"""
WebSocket API 路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json

from app.main import manager

router = APIRouter()


@router.websocket("/ws/alerts")
async def websocket_alerts(
    websocket: WebSocket,
    alert_id: Optional[int] = Query(None, description="告警ID，不传则接收所有告警")
):
    """
    WebSocket 端点：实时告警推送
    
    连接后发送：
    - ping: 心跳检测
    - subscribe:{alert_id}: 订阅特定告警
    
    接收：
    - 所有告警更新（无 alert_id 时）
    - 指定告警更新（有 alert_id 时）
    """
    await manager.connect(websocket, alert_id)
    
    try:
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "alert_id": alert_id,
            "message": "WebSocket 连接成功"
        })
        
        while True:
            data = await websocket.receive_text()
            
            # 心跳
            if data == "ping":
                await websocket.send_text("pong")
                continue
            
            # 订阅特定告警
            if data.startswith("subscribe:"):
                try:
                    target_alert_id = int(data.split(":")[1])
                    await manager.connect(websocket, target_alert_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "alert_id": target_alert_id
                    })
                except (ValueError, IndexError):
                    await websocket.send_json({
                        "type": "error",
                        "message": "无效的告警ID"
                    })
                continue
            
            # 取消订阅
            if data.startswith("unsubscribe:"):
                try:
                    target_alert_id = int(data.split(":")[1])
                    manager.disconnect(websocket, target_alert_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "alert_id": target_alert_id
                    })
                except (ValueError, IndexError):
                    pass
                continue
            
            # 解析 JSON 消息
            try:
                message = json.loads(data)
                # 处理客户端消息
                if message.get("type") == "heartbeat":
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "timestamp": message.get("timestamp")
                    })
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, alert_id)
