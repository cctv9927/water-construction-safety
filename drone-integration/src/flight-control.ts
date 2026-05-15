/**
 * 航线控制模块 - 管理无人机航线和飞行控制
 */

import { EventEmitter } from 'events';

// 坐标类型
interface Coordinate {
  latitude: number;
  longitude: number;
  altitude: number;
}

// 航点类型
interface Waypoint {
  id: string;
  index: number;
  position: Coordinate;
  heading: number;       // 航向角 (0-360)
  speed: number;         // 飞行速度 (m/s)
  stayTime: number;      // 停留时间 (秒)
  action: WaypointAction;
  params: Record<string, any>;
}

// 航点动作
enum WaypointAction {
  STAY = 'stay',           // 悬停
  TAKE_PHOTO = 'take_photo',   // 拍照
  START_RECORD = 'start_record', // 开始录像
  STOP_RECORD = 'stop_record',   // 停止录像
  ROTATE = 'rotate',       // 旋转
  PAYLOAD_CONTROL = 'payload_control', // 云台控制
}

// 航线任务
interface WaypointMission {
  id: string;
  name: string;
  waypoints: Waypoint[];
  repeat: boolean;         // 是否循环执行
  flySpeed: number;        // 飞行速度
  finishAction: FinishAction;
}

// 任务完成动作
enum FinishAction {
  HOVER = 'hover',         // 悬停
  GO_HOME = 'go_home',     // 返航
  LAND = 'land',           // 降落
}

// 飞行状态
interface FlightState {
  isFlying: boolean;
  isMissionActive: boolean;
  currentWaypoint: number;
  missionProgress: number;
  estimatedTime: number;   // 预计剩余时间 (秒)
  distanceToNext: number;  // 到下一航点距离 (米)
  totalDistance: number;   // 总航程 (米)
}

// 航线控制配置
interface FlightControlConfig {
  droneId: string;
  maxSpeed: number;        // 最大速度 (m/s)
  minSpeed: number;        // 最小速度 (m/s)
  defaultAltitude: number; // 默认高度 (米)
  maxAltitude: number;     // 最大高度 (米)
  minAltitude: number;     // 最小高度 (米)
  homeAltitude: number;    // 返航高度 (米)
}

/**
 * 航线控制器
 */
export class FlightController extends EventEmitter {
  private config: FlightControlConfig;
  private currentMission: WaypointMission | null = null;
  private flightState: FlightState;
  private droneAdapter: DroneAdapter;

  constructor(
    droneAdapter: DroneAdapter,
    config: Partial<FlightControlConfig> = {}
  ) {
    super();

    this.droneAdapter = droneAdapter;

    this.config = {
      droneId: config.droneId || 'DRONE_001',
      maxSpeed: config.maxSpeed || 15,
      minSpeed: config.minSpeed || 1,
      defaultAltitude: config.defaultAltitude || 100,
      maxAltitude: config.maxAltitude || 500,
      minAltitude: config.minAltitude || 20,
      homeAltitude: config.homeAltitude || 50,
    };

    this.flightState = {
      isFlying: false,
      isMissionActive: false,
      currentWaypoint: 0,
      missionProgress: 0,
      estimatedTime: 0,
      distanceToNext: 0,
      totalDistance: 0,
    };
  }

  /**
   * 加载航线任务
   */
  async loadMission(mission: WaypointMission): Promise<void> {
    // 验证航线
    this.validateMission(mission);

    this.currentMission = mission;

    // 计算总航程
    this.flightState.totalDistance = this.calculateTotalDistance(mission.waypoints);

    console.log(`[FlightCtrl] 航线已加载: ${mission.name}`);
    console.log(`[FlightCtrl] 航点数: ${mission.waypoints.length}`);
    console.log(`[FlightCtrl] 总航程: ${this.flightState.totalDistance.toFixed(2)}m`);

    this.emit('mission_loaded', {
      missionId: mission.id,
      waypointCount: mission.waypoints.length,
      totalDistance: this.flightState.totalDistance
    });
  }

  /**
   * 验证航线
   */
  private validateMission(mission: WaypointMission): void {
    if (mission.waypoints.length < 2) {
      throw new Error('航线至少需要2个航点');
    }

    for (const wp of mission.waypoints) {
      // 验证高度
      if (wp.position.altitude < this.config.minAltitude) {
        wp.position.altitude = this.config.minAltitude;
      }
      if (wp.position.altitude > this.config.maxAltitude) {
        throw new Error(`航点 ${wp.id} 高度超过限制`);
      }

      // 验证速度
      if (wp.speed < this.config.minSpeed) {
        wp.speed = this.config.minSpeed;
      }
      if (wp.speed > this.config.maxSpeed) {
        wp.speed = this.config.maxSpeed;
      }
    }
  }

  /**
   * 执行航线任务
   */
  async executeMission(): Promise<void> {
    if (!this.currentMission) {
      throw new Error('未加载航线任务');
    }

    if (!this.flightState.isFlying) {
      throw new Error('无人机未起飞');
    }

    console.log(`[FlightCtrl] 开始执行航线: ${this.currentMission.name}`);

    this.flightState.isMissionActive = true;
    this.flightState.currentWaypoint = 0;

    this.emit('mission_started', { missionId: this.currentMission.id });

    // 按顺序飞向每个航点
    for (let i = 0; i < this.currentMission.waypoints.length; i++) {
      if (!this.flightState.isMissionActive) {
        break;
      }

      const waypoint = this.currentMission.waypoints[i];
      this.flightState.currentWaypoint = i;
      this.flightState.missionProgress = (i / this.currentMission.waypoints.length) * 100;

      console.log(`[FlightCtrl] 飞向航点 ${i + 1}/${this.currentMission.waypoints.length}`);

      this.emit('waypoint_started', {
        index: i,
        waypoint: waypoint
      });

      // 执行航点动作
      await this.executeWaypointAction(waypoint);

      // 移动到航点
      await this.droneAdapter.flyTo(waypoint.position);

      // 悬停等待
      if (waypoint.stayTime > 0) {
        await this.delay(waypoint.stayTime * 1000);
      }

      this.emit('waypoint_completed', {
        index: i,
        waypoint: waypoint
      });
    }

    // 任务完成
    this.flightState.isMissionActive = false;
    this.flightState.missionProgress = 100;

    console.log(`[FlightCtrl] 航线完成: ${this.currentMission.name}`);

    this.emit('mission_completed', {
      missionId: this.currentMission.id
    });

    // 执行完成动作
    await this.executeFinishAction();
  }

  /**
   * 执行航点动作
   */
  private async executeWaypointAction(waypoint: Waypoint): Promise<void> {
    switch (waypoint.action) {
      case WaypointAction.TAKE_PHOTO:
        console.log('[FlightCtrl] 拍照');
        await this.droneAdapter.takePhoto();
        break;

      case WaypointAction.START_RECORD:
        console.log('[FlightCtrl] 开始录像');
        await this.droneAdapter.startRecord();
        break;

      case WaypointAction.STOP_RECORD:
        console.log('[FlightCtrl] 停止录像');
        await this.droneAdapter.stopRecord();
        break;

      case WaypointAction.ROTATE:
        console.log(`[FlightCtrl] 旋转: ${waypoint.heading}°`);
        await this.droneAdapter.rotate(waypoint.heading);
        break;

      case WaypointAction.PAYLOAD_CONTROL:
        console.log('[FlightCtrl] 云台控制', waypoint.params);
        await this.droneAdapter.controlPayload(waypoint.params);
        break;

      default:
        // STAY - 悬停
        break;
    }
  }

  /**
   * 执行完成动作
   */
  private async executeFinishAction(): Promise<void> {
    if (!this.currentMission) return;

    switch (this.currentMission.finishAction) {
      case FinishAction.GO_HOME:
        console.log('[FlightCtrl] 返航');
        await this.droneAdapter.goHome();
        break;

      case FinishAction.LAND:
        console.log('[FlightCtrl] 降落');
        await this.droneAdapter.land();
        break;

      default:
        // HOVER - 悬停
        break;
    }
  }

  /**
   * 停止任务
   */
  async stopMission(): Promise<void> {
    console.log('[FlightCtrl] 停止任务');
    this.flightState.isMissionActive = false;

    await this.droneAdapter.hover();

    this.emit('mission_stopped', {
      missionId: this.currentMission?.id,
      stoppedAt: this.flightState.currentWaypoint
    });
  }

  /**
   * 计算总航程
   */
  private calculateTotalDistance(waypoints: Waypoint[]): number {
    let total = 0;

    for (let i = 1; i < waypoints.length; i++) {
      const prev = waypoints[i - 1].position;
      const curr = waypoints[i].position;
      total += this.haversineDistance(prev, curr);
    }

    return total;
  }

  /**
   * 使用 Haversine 公式计算两点间距离
   */
  private haversineDistance(coord1: Coordinate, coord2: Coordinate): number {
    const R = 6371000; // 地球半径 (米)
    const lat1 = coord1.latitude * Math.PI / 180;
    const lat2 = coord2.latitude * Math.PI / 180;
    const dLat = (coord2.latitude - coord1.latitude) * Math.PI / 180;
    const dLon = (coord2.longitude - coord1.longitude) * Math.PI / 180;

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    // 水平距离
    const horizontal = R * c;

    // 加上高度差
    const vertical = Math.abs(coord2.altitude - coord1.altitude);

    return Math.sqrt(horizontal * horizontal + vertical * vertical);
  }

  /**
   * 延迟函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 获取飞行状态
   */
  getFlightState(): FlightState {
    return { ...this.flightState };
  }

  /**
   * 获取当前任务
   */
  getCurrentMission(): WaypointMission | null {
    return this.currentMission ? { ...this.currentMission } : null;
  }

  /**
   * 获取配置
   */
  getConfig(): FlightControlConfig {
    return { ...this.config };
  }
}

/**
 * 无人机适配器接口
 * 实际对接 DJI SDK 或模拟器
 */
export interface DroneAdapter {
  takeoff(): Promise<void>;
  land(): Promise<void>;
  goHome(): Promise<void>;
  hover(): Promise<void>;
  flyTo(position: Coordinate): Promise<void>;
  rotate(heading: number): Promise<void>;
  takePhoto(): Promise<void>;
  startRecord(): Promise<void>;
  stopRecord(): Promise<void>;
  controlPayload(params: Record<string, any>): Promise<void>;
  getPosition(): Promise<Coordinate>;
  getBattery(): Promise<number>;
}

export {
  FlightController,
  FlightControlConfig,
  FlightState,
  WaypointMission,
  Waypoint,
  WaypointAction,
  Coordinate
};
