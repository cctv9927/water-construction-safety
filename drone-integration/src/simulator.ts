/**
 * 无人机模拟器 - 在没有真实无人机时提供 Mock 数据
 */

import { EventEmitter } from 'events';
import WebSocket from 'ws';

// 地理坐标类型
interface Coordinate {
  latitude: number;
  longitude: number;
  altitude: number;
}

// 无人机状态
interface DroneState {
  droneId: string;
  connected: boolean;
  batteryLevel: number;
  position: Coordinate;
  heading: number;
  speed: number;
  altitude: number;
  isFlying: boolean;
  gpsSignal: number;
  homePoint: Coordinate;
  flightMode: string;
  timestamp: number;
}

// 航线航点
interface Waypoint {
  position: Coordinate;
  heading: number;
  action: string;
  stayTime: number;
}

// 模拟配置
interface SimulatorConfig {
  droneId: string;
  initialPosition: Coordinate;
  homePosition: Coordinate;
  updateInterval: number; // ms
  wsPort: number;
}

/**
 * 无人机模拟器
 * 生成模拟的无人机状态数据，通过 WebSocket 推送
 */
export class DroneSimulator extends EventEmitter {
  private config: SimulatorConfig;
  private state: DroneState;
  private waypoints: Waypoint[] = [];
  private currentWaypointIndex: number = 0;
  private isAutoFlying: boolean = false;
  private intervalId: NodeJS.Timeout | null = null;
  private wsServer: WebSocket.Server | null = null;
  private clients: Set<WebSocket> = new Set();

  constructor(config: Partial<SimulatorConfig> = {}) {
    super();

    this.config = {
      droneId: config.droneId || 'SIM_001',
      initialPosition: config.initialPosition || {
        latitude: 31.2304,
        longitude: 121.4737,
        altitude: 100
      },
      homePosition: config.homePosition || {
        latitude: 31.2304,
        longitude: 121.4737,
        altitude: 0
      },
      updateInterval: config.updateInterval || 200,
      wsPort: config.wsPort || 8082,
    };

    // 初始化状态
    this.state = {
      droneId: this.config.droneId,
      connected: false,
      batteryLevel: 100,
      position: { ...this.config.initialPosition },
      heading: 0,
      speed: 0,
      altitude: this.config.initialPosition.altitude,
      isFlying: false,
      gpsSignal: 5,
      homePoint: { ...this.config.homePosition },
      flightMode: 'P-GPS',
      timestamp: Date.now(),
    };
  }

  /**
   * 启动模拟器
   */
  async start(): Promise<void> {
    return new Promise((resolve) => {
      console.log(`[Simulator] 无人机模拟器启动: ${this.config.droneId}`);
      console.log(`[Simulator] WebSocket 端口: ${this.config.wsPort}`);

      // 创建 WebSocket 服务器
      this.wsServer = new WebSocket.Server({ port: this.config.wsPort });

      this.wsServer.on('connection', (ws) => {
        console.log('[Simulator] 客户端连接');
        this.clients.add(ws);

        // 发送初始状态
        ws.send(JSON.stringify({
          type: 'drone_state',
          data: this.getState()
        }));

        ws.on('close', () => {
          console.log('[Simulator] 客户端断开');
          this.clients.delete(ws);
        });

        ws.on('message', (message) => {
          try {
            const msg = JSON.parse(message.toString());
            this.handleCommand(msg);
          } catch (e) {
            console.error('[Simulator] 解析命令失败:', e);
          }
        });
      });

      // 模拟连接延迟
      setTimeout(() => {
        this.state.connected = true;
        this.broadcastState();
        console.log('[Simulator] 无人机已连接（模拟）');
        resolve();
      }, 1000);
    });
  }

  /**
   * 停止模拟器
   */
  stop(): void {
    console.log('[Simulator] 正在停止...');

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    if (this.wsServer) {
      this.wsServer.close();
      this.wsServer = null;
    }

    this.state.connected = false;
    this.isAutoFlying = false;
    console.log('[Simulator] 已停止');
  }

  /**
   * 开始飞行模拟
   */
  async takeoff(): Promise<void> {
    if (!this.state.connected) {
      throw new Error('无人机未连接');
    }

    console.log('[Simulator] 起飞...');
    this.state.isFlying = true;
    this.state.flightMode = 'AUTO';
    this.state.altitude = 50;

    // 启动状态更新循环
    this.startUpdateLoop();
    this.broadcastState();
  }

  /**
   * 降落
   */
  async land(): Promise<void> {
    console.log('[Simulator] 降落...');
    this.state.isFlying = false;
    this.state.speed = 0;
    this.state.flightMode = 'LAND';
    this.broadcastState();
  }

  /**
   * 设置航线
   */
  setWaypoints(waypoints: Waypoint[]): void {
    this.waypoints = waypoints;
    this.currentWaypointIndex = 0;
    console.log(`[Simulator] 已设置 ${waypoints.length} 个航点`);
  }

  /**
   * 开始自动航线飞行
   */
  async startWaypointMission(): Promise<void> {
    if (!this.state.isFlying) {
      throw new Error('请先起飞');
    }

    if (this.waypoints.length === 0) {
      throw new Error('未设置航线');
    }

    console.log('[Simulator] 开始航线任务...');
    this.isAutoFlying = true;
    this.flyToNextWaypoint();
  }

  /**
   * 飞向下一个航点
   */
  private flyToNextWaypoint(): void {
    if (!this.isAutoFlying || this.currentWaypointIndex >= this.waypoints.length) {
      console.log('[Simulator] 航线任务完成');
      this.isAutoFlying = false;
      return;
    }

    const target = this.waypoints[this.currentWaypointIndex];
    console.log(`[Simulator] 飞向航点 ${this.currentWaypointIndex + 1}/${this.waypoints.length}`);

    // 简化：直接移动到目标位置
    const moveInterval = setInterval(() => {
      const dx = target.position.latitude - this.state.position.latitude;
      const dy = target.position.longitude - this.state.position.longitude;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance < 0.0001) {
        // 到达航点
        this.state.position = { ...target.position };
        this.state.altitude = target.position.altitude;
        this.state.heading = target.heading;
        this.state.speed = 0;
        clearInterval(moveInterval);

        this.emit('waypoint_reached', {
          index: this.currentWaypointIndex,
          waypoint: target
        });

        // 等待停留时间后飞向下一个
        setTimeout(() => {
          this.currentWaypointIndex++;
          this.flyToNextWaypoint();
        }, target.stayTime * 1000);
      } else {
        // 移动中
        const step = 0.00005;
        this.state.position.latitude += Math.sign(dx) * Math.min(step, Math.abs(dx));
        this.state.position.longitude += Math.sign(dy) * Math.min(step, Math.abs(dy));
        this.state.speed = 5;
        this.state.heading = Math.atan2(dy, dx) * (180 / Math.PI);
      }
    }, 200);
  }

  /**
   * 移动到指定位置
   */
  async goTo(position: Coordinate): Promise<void> {
    console.log(`[Simulator] 飞向: ${position.latitude}, ${position.longitude}, ${position.altitude}m`);
    
    // 简化实现：直接设置位置
    this.state.position = { ...position };
    this.state.altitude = position.altitude;
    this.broadcastState();
  }

  /**
   * 启动状态更新循环
   */
  private startUpdateLoop(): void {
    if (this.intervalId) return;

    this.intervalId = setInterval(() => {
      this.updateSimulation();
      this.broadcastState();
    }, this.config.updateInterval);
  }

  /**
   * 更新模拟状态
   */
  private updateSimulation(): void {
    if (!this.state.isFlying) return;

    // 模拟电池消耗
    this.state.batteryLevel = Math.max(0, this.state.batteryLevel - 0.01);

    // 模拟 GPS 信号波动
    this.state.gpsSignal = Math.random() > 0.95 ? 4 : 5;

    // 模拟位置轻微抖动
    this.state.position.latitude += (Math.random() - 0.5) * 0.00001;
    this.state.position.longitude += (Math.random() - 0.5) * 0.00001;

    // 模拟高度变化
    if (this.state.speed > 0) {
      this.state.altitude = Math.max(
        10,
        this.state.altitude + (Math.random() - 0.5) * 0.5
      );
    }

    this.state.timestamp = Date.now();
  }

  /**
   * 处理控制命令
   */
  private handleCommand(command: any): void {
    console.log('[Simulator] 收到命令:', command.type);

    switch (command.type) {
      case 'takeoff':
        this.takeoff().catch(console.error);
        break;
      case 'land':
        this.land();
        break;
      case 'go_to':
        if (command.position) {
          this.goTo(command.position);
        }
        break;
      case 'set_home':
        this.state.homePoint = command.position || this.state.position;
        break;
      case 'set_waypoints':
        if (command.waypoints) {
          this.setWaypoints(command.waypoints);
        }
        break;
      case 'start_mission':
        this.startWaypointMission().catch(console.error);
        break;
      case 'get_state':
        this.broadcast({ type: 'drone_state', data: this.getState() });
        break;
    }
  }

  /**
   * 广播消息到所有客户端
   */
  private broadcast(message: any): void {
    const data = JSON.stringify(message);
    this.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(data);
      }
    });
  }

  /**
   * 广播当前状态
   */
  private broadcastState(): void {
    this.broadcast({
      type: 'drone_state',
      data: this.getState()
    });
  }

  /**
   * 获取当前状态
   */
  getState(): DroneState {
    return { ...this.state };
  }

  /**
   * 获取配置
   */
  getConfig(): SimulatorConfig {
    return { ...this.config };
  }
}

// 航点航拍任务类型
export interface InspectionWaypoint extends Waypoint {
  id: string;
  inspectionType: 'photo' | 'video' | 'thermal' | 'LiDAR';
  photoCount: number;
  hoverDuration: number; // 秒
  gimbalAngle: { pitch: number; roll: number; yaw: number };
}

// 巡检任务类型
export interface InspectionMission {
  missionId: string;
  name: string;
  waypoints: InspectionWaypoint[];
  totalDistance: number; // km
  estimatedDuration: number; // minutes
  startTime: number;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
}

// 视频流传输出类型
export interface VideoStreamConfig {
  enabled: boolean;
  codec: 'h264' | 'h265' | 'mjpeg';
  bitrate: number; // kbps
  resolution: { width: number; height: number };
  fps: number;
  keyframeInterval: number; // seconds
}

// 模拟巡检区域定义
const INSPECTION_ZONES = [
  {
    zoneId: 'ZONE-A',
    name: '水库大坝区域',
    center: { latitude: 29.6501, longitude: 91.1001, altitude: 0 },
    radius: 0.005, // 约500米
    riskLevel: 'high',
  },
  {
    zoneId: 'ZONE-B',
    name: '高边坡监测区',
    center: { latitude: 29.6503, longitude: 91.1003, altitude: 0 },
    radius: 0.003, // 约300米
    riskLevel: 'critical',
  },
  {
    zoneId: 'ZONE-C',
    name: '施工材料堆放区',
    center: { latitude: 29.6505, longitude: 91.1005, altitude: 0 },
    radius: 0.002,
    riskLevel: 'medium',
  },
  {
    zoneId: 'ZONE-D',
    name: '人员活动区域',
    center: { latitude: 29.6507, longitude: 91.1007, altitude: 0 },
    radius: 0.002,
    riskLevel: 'medium',
  },
];

/**
 * 生成巡检航点数据
 */
function generateInspectionWaypoints(missionId: string): InspectionWaypoint[] {
  const waypoints: InspectionWaypoint[] = [];
  const zone = INSPECTION_ZONES[Math.floor(Math.random() * INSPECTION_ZONES.length)];
  
  // 生成5-10个航点
  const waypointCount = Math.floor(Math.random() * 6) + 5;
  
  for (let i = 0; i < waypointCount; i++) {
    const angle = (i / waypointCount) * 2 * Math.PI;
    const distance = zone.radius * (0.5 + Math.random() * 0.5);
    
    waypoints.push({
      id: `WP-${missionId}-${i + 1}`,
      position: {
        latitude: zone.center.latitude + Math.cos(angle) * distance,
        longitude: zone.center.longitude + Math.sin(angle) * distance,
        altitude: 30 + Math.random() * 70, // 30-100米
      },
      heading: Math.floor(Math.random() * 360),
      action: 'inspection',
      stayTime: 5 + Math.floor(Math.random() * 10),
      inspectionType: ['photo', 'video', 'thermal'][Math.floor(Math.random() * 3)] as any,
      photoCount: Math.floor(Math.random() * 10) + 1,
      hoverDuration: 5 + Math.floor(Math.random() * 15),
      gimbalAngle: {
        pitch: -30 - Math.floor(Math.random() * 30),
        roll: Math.floor(Math.random() * 10) - 5,
        yaw: Math.floor(Math.random() * 360),
      },
    });
  }
  
  return waypoints;
}

/**
 * 创建模拟巡检任务
 */
function createMockInspectionMission(): InspectionMission {
  const missionId = `MISSION-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`;
  const waypoints = generateInspectionWaypoints(missionId);
  
  return {
    missionId,
    name: `日常巡检任务-${new Date().toLocaleDateString()}`,
    waypoints,
    totalDistance: Math.round(Math.random() * 5 * 10) / 10,
    estimatedDuration: waypoints.length * 3,
    startTime: Date.now(),
    status: 'pending',
  };
}

/**
 * 生成视频流传配置
 */
function generateVideoStreamConfig(): VideoStreamConfig {
  return {
    enabled: true,
    codec: 'h264',
    bitrate: 2000 + Math.floor(Math.random() * 3000),
    resolution: { width: 1920, height: 1080 },
    fps: 25,
    keyframeInterval: 2,
  };
}

/**
 * 模拟视频流帧数据
 */
function generateVideoFrameData(): any {
  return {
    frameId: Math.floor(Math.random() * 1000000),
    timestamp: Date.now(),
    sequenceNumber: Math.floor(Math.random() * 10000),
    size: 50000 + Math.floor(Math.random() * 100000), // bytes
    keyframe: Math.random() > 0.9,
    metadata: {
      encoding: 'h264',
      profile: 'High',
      level: '4.1',
      resolution: '1920x1080',
      fps: 25,
    },
  };
}

/**
 * 模拟航点飞行状态
 */
function generateWaypointFlightData(waypoint: InspectionWaypoint, progress: number): any {
  return {
    waypointId: waypoint.id,
    progress: Math.min(100, progress),
    distanceToWaypoint: Math.max(0, 100 - progress) * 0.5, // 米
    estimatedArrival: Date.now() + (100 - progress) * 100,
    gimbalAngle: waypoint.gimbalAngle,
    zoomLevel: 1 + Math.floor(Math.random() * 3),
    focusDistance: 10 + Math.floor(Math.random() * 90),
  };
}
async function main() {
  const simulator = new DroneSimulator({
    droneId: process.argv.includes('--simulator') ? 'SIM_001' : 'DRONE_001',
    wsPort: parseInt(process.env.WS_PORT || '8082'),
  });

  // 处理进程退出
  process.on('SIGINT', () => {
    simulator.stop();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    simulator.stop();
    process.exit(0);
  });

  await simulator.start();

  // 检查是否为模拟巡检模式
  const inspectionMode = process.argv.includes('--inspection');
  
  if (inspectionMode) {
    console.log('[Simulator] 启动模拟巡检模式...');
    console.log('[Simulator] 模拟区域列表:');
    INSPECTION_ZONES.forEach(zone => {
      console.log(`  - ${zone.zoneId}: ${zone.name} (风险等级: ${zone.riskLevel})`);
    });
    console.log();
    
    // 启动无人机
    await simulator.takeoff();
    
    // 创建模拟巡检任务
    const mission = createMockInspectionMission();
    console.log(`[Simulator] 创建巡检任务: ${mission.name}`);
    console.log(`[Simulator] 任务ID: ${mission.missionId}`);
    console.log(`[Simulator] 航点数量: ${mission.waypoints.length}`);
    console.log(`[Simulator] 预计航程: ${mission.totalDistance} km`);
    console.log(`[Simulator] 预计时长: ${mission.estimatedDuration} 分钟`);
    console.log();
    
    // 模拟视频流传输出
    const videoConfig = generateVideoStreamConfig();
    console.log(`[Simulator] 视频流配置:`);
    console.log(`  - 编码: ${videoConfig.codec}`);
    console.log(`  - 码率: ${videoConfig.bitrate} kbps`);
    console.log(`  - 分辨率: ${videoConfig.resolution.width}x${videoConfig.resolution.height}`);
    console.log(`  - 帧率: ${videoConfig.fps} fps`);
    console.log();
    
    // 设置航线
    const waypoints = mission.waypoints.map(wp => ({
      position: wp.position,
      heading: wp.heading,
      action: wp.action,
      stayTime: wp.stayTime,
    }));
    simulator.setWaypoints(waypoints);
    
    // 开始航点飞行
    simulator.on('waypoint_reached', (data: any) => {
      console.log(`[Simulator] 到达航点 ${data.index + 1}/${mission.waypoints.length}`);
      console.log(`  位置: ${data.waypoint.position.latitude.toFixed(6)}, ${data.waypoint.position.longitude.toFixed(6)}`);
      console.log(`  高度: ${data.waypoint.position.altitude.toFixed(1)}m`);
      console.log(`  检查类型: ${data.waypoint.inspectionType}`);
      console.log(`  拍照数量: ${data.waypoint.photoCount}`);
      
      // 模拟在此航点采集数据
      console.log('  采集数据中...');
      console.log(`  ✓ 航拍照片: ${data.waypoint.photoCount} 张`);
      console.log(`  ✓ 视频片段: ${data.waypoint.hoverDuration} 秒`);
      console.log();
    });
    
    // 开始视频流传输出模拟
    const videoStreamInterval = setInterval(() => {
      const frameData = generateVideoFrameData();
      // 模拟视频帧数据输出（实际项目中会发送到WebSocket）
      if (frameData.keyframe) {
        console.log(`[VideoStream] 关键帧 ID=${frameData.frameId} 大小=${frameData.size} bytes`);
      }
    }, 1000 / videoConfig.fps);
    
    // 开始航点任务
    await simulator.startWaypointMission();
    
    // 任务完成
    setTimeout(async () => {
      console.log('[Simulator] 巡检任务完成，准备返航...');
      await simulator.land();
      
      // 汇总
      console.log();
      console.log('='.repeat(50));
      console.log('巡检任务汇总');
      console.log('='.repeat(50));
      console.log(`任务ID: ${mission.missionId}`);
      console.log(`完成任务: ${mission.waypoints.length} 个航点`);
      console.log(`飞行时长: ${mission.estimatedDuration} 分钟`);
      console.log(`采集照片: ${mission.waypoints.reduce((sum: number, wp: any) => sum + wp.photoCount, 0)} 张`);
      console.log(`采集视频: ${mission.waypoints.reduce((sum: number, wp: any) => sum + wp.hoverDuration, 0)} 秒`);
      console.log(`电池消耗: ${Math.round((100 - simulator.getState().batteryLevel) * 10) / 10}%`);
      console.log('='.repeat(50));
      
      clearInterval(videoStreamInterval);
      simulator.stop();
      process.exit(0);
    }, mission.waypoints.length * mission.estimatedDuration * 1000 / 2); // 加速模拟
    
  } else {
    console.log('[Simulator] 等待命令...');
    console.log('[Simulator] 可用命令: takeoff, land, go_to, set_waypoints, start_mission');
    console.log('[Simulator] 巡检模式: --inspection');
  }
}

if (require.main === module) {
  main().catch(console.error);
}

export { DroneSimulator, SimulatorConfig, DroneState, Waypoint, Coordinate, InspectionWaypoint, InspectionMission, VideoStreamConfig };
