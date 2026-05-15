# 无人机集成模块 (drone-integration)

## 模块概述

负责与 DJI 无人机集成，支持实时视频流回传、航线规划与控制。

## 技术栈

- **语言**: TypeScript
- **运行环境**: Node.js 18+
- **通信**: WebSocket
- **视频流**: 支持 RTMP → WebRTC 转换

## 核心功能

### 1. 模拟模式
- 无真实无人机时，使用模拟器生成 Mock 数据
- 模拟飞行轨迹、电池消耗、GPS 信号等
- 支持 WebSocket 实时推送状态

### 2. 视频流转发
- 从无人机接收视频流
- 转发到多个客户端
- 支持帧缓冲和统计

### 3. 航线控制
- 创建和管理航线任务
- 执行航点飞行
- 支持悬停、拍照、录像等动作

## 目录结构

```
drone-integration/
├── src/
│   ├── index.ts          # 主入口
│   ├── simulator.ts      # 模拟器
│   ├── video-relay.ts    # 视频流转发
│   └── flight-control.ts  # 航线控制
├── package.json
├── tsconfig.json
└── README.md
```

## 安装与运行

```bash
# 安装依赖
npm install

# 编译 TypeScript
npm run build

# 运行（模拟模式）
npm run dev:simulator

# 运行（真实无人机模式）
npm start
```

## WebSocket 接口

### 状态订阅
```
ws://localhost:8082
```

### 消息格式

#### 无人机状态
```json
{
  "type": "drone_state",
  "data": {
    "droneId": "SIM_001",
    "connected": true,
    "batteryLevel": 98,
    "position": {
      "latitude": 31.2304,
      "longitude": 121.4737,
      "altitude": 50
    },
    "heading": 180,
    "speed": 5,
    "isFlying": true,
    "gpsSignal": 5
  }
}
```

#### 控制命令
```json
// 起飞
{ "type": "takeoff" }

// 降落
{ "type": "land" }

// 飞向指定位置
{ "type": "go_to", "position": { "latitude": 31.23, "longitude": 121.47, "altitude": 100 } }

// 设置航点
{ "type": "set_waypoints", "waypoints": [...] }

// 开始航线任务
{ "type": "start_mission" }

// 获取状态
{ "type": "get_state" }
```

## 使用示例

```typescript
import { DroneIntegration } from './src/index';

const drone = new DroneIntegration({
  mode: 'simulator',
  droneId: 'DRONE_001',
  wsPort: 8082,
});

// 初始化
await drone.init();

// 起飞
await drone.takeoff();

// 降落
await drone.land();

// 获取状态
const status = drone.getStatus();
console.log(status);

// 停止
await drone.stop();
```

## 真实无人机集成

要连接真实 DJI 无人机：

1. 获取 DJI SDK 授权
2. 在 DJI Developer Platform 注册应用
3. 获取 App Key 和 Secret
4. 替换 `index.ts` 中的 `RealDroneAdapter` 实现

注意：真实无人机控制需要适当的飞行许可和安全措施。
