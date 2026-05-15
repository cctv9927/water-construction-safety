/**
 * 无人机集成模块入口
 * 支持 DJI SDK 和模拟模式
 */

import { DroneSimulator } from './simulator';
import { VideoRelay } from './video-relay';
import { FlightController, DroneAdapter } from './flight-control';

// 模式类型
type DroneMode = 'real' | 'simulator';

// 配置类型
interface DroneIntegrationConfig {
  mode: DroneMode;
  droneId: string;
  wsPort: number;
  videoPort: number;
  iotHubUrl: string;
}

/**
 * 适配器：将模拟器适配为 DroneAdapter
 */
class SimulatorAdapter implements DroneAdapter {
  private simulator: DroneSimulator;

  constructor(simulator: DroneSimulator) {
    this.simulator = simulator;
  }

  async takeoff(): Promise<void> {
    await this.simulator.takeoff();
  }

  async land(): Promise<void> {
    await this.simulator.land();
  }

  async goHome(): Promise<void> {
    // 模拟器不支持直接返航，使用移动到 home 位置
    const state = this.simulator.getState();
    await this.simulator.goTo(state.homePoint);
  }

  async hover(): Promise<void> {
    // 模拟器中直接停止移动即可
  }

  async flyTo(position: { latitude: number; longitude: number; altitude: number }): Promise<void> {
    await this.simulator.goTo(position);
  }

  async rotate(heading: number): Promise<void> {
    console.log(`[Adapter] 旋转到 ${heading}°`);
  }

  async takePhoto(): Promise<void> {
    console.log('[Adapter] 拍照');
  }

  async startRecord(): Promise<void> {
    console.log('[Adapter] 开始录像');
  }

  async stopRecord(): Promise<void> {
    console.log('[Adapter] 停止录像');
  }

  async controlPayload(params: Record<string, any>): Promise<void> {
    console.log('[Adapter] 云台控制:', params);
  }

  async getPosition(): Promise<{ latitude: number; longitude: number; altitude: number }> {
    const state = this.simulator.getState();
    return state.position;
  }

  async getBattery(): Promise<number> {
    const state = this.simulator.getState();
    return state.batteryLevel;
  }
}

/**
 * 无人机集成主类
 */
export class DroneIntegration {
  private config: DroneIntegrationConfig;
  private simulator: DroneSimulator | null = null;
  private videoRelay: VideoRelay | null = null;
  private flightController: FlightController | null = null;
  private adapter: DroneAdapter | null = null;

  constructor(config: Partial<DroneIntegrationConfig> = {}) {
    this.config = {
      mode: config.mode || (process.env.DRONE_MODE as DroneMode) || 'simulator',
      droneId: config.droneId || process.env.DRONE_ID || 'DRONE_001',
      wsPort: config.wsPort || parseInt(process.env.WS_PORT || '8082'),
      videoPort: config.videoPort || parseInt(process.env.VIDEO_PORT || '8084'),
      iotHubUrl: config.iotHubUrl || process.env.IOT_HUB_URL || 'http://localhost:8000',
    };
  }

  /**
   * 初始化
   */
  async init(): Promise<void> {
    console.log('='.repeat(50));
    console.log('无人机集成模块初始化');
    console.log(`模式: ${this.config.mode}`);
    console.log(`无人机ID: ${this.config.droneId}`);
    console.log('='.repeat(50));

    if (this.config.mode === 'simulator') {
      await this.initSimulator();
    } else {
      await this.initRealDrone();
    }

    // 初始化视频转发
    this.initVideoRelay();

    console.log('初始化完成');
  }

  /**
   * 初始化模拟器
   */
  private async initSimulator(): Promise<void> {
    console.log('[Init] 启动模拟器...');

    this.simulator = new DroneSimulator({
      droneId: this.config.droneId,
      wsPort: this.config.wsPort,
    });

    await this.simulator.start();

    this.adapter = new SimulatorAdapter(this.simulator);

    this.flightController = new FlightController(this.adapter, {
      droneId: this.config.droneId,
    });

    console.log('[Init] 模拟器已启动');
  }

  /**
   * 初始化真实无人机（需要 DJI SDK）
   */
  private async initRealDrone(): Promise<void> {
    console.log('[Init] 连接真实无人机...');

    // 真实 DJI SDK 集成示例
    // 注意: 实际需要 DJI SDK 库和相应权限
    // 这里使用占位实现

    class RealDroneAdapter implements DroneAdapter {
      async takeoff(): Promise<void> {
        // TODO: 调用 DJI SDK
        console.log('[RealDrone] 调用 SDK: takeoff');
      }

      async land(): Promise<void> {
        console.log('[RealDrone] 调用 SDK: land');
      }

      async goHome(): Promise<void> {
        console.log('[RealDrone] 调用 SDK: goHome');
      }

      async hover(): Promise<void> {
        console.log('[RealDrone] 调用 SDK: hover');
      }

      async flyTo(position: { latitude: number; longitude: number; altitude: number }): Promise<void> {
        console.log('[RealDrone] 调用 SDK: flyTo', position);
      }

      async rotate(heading: number): Promise<void> {
        console.log('[RealDrone] 调用 SDK: rotate', heading);
      }

      async takePhoto(): Promise<void> {
        console.log('[RealDrone] 调用 SDK: takePhoto');
      }

      async startRecord(): Promise<void> {
        console.log('[RealDrone] 调用 SDK: startRecord');
      }

      async stopRecord(): Promise<void> {
        console.log('[RealDrone] 调用 SDK: stopRecord');
      }

      async controlPayload(params: Record<string, any>): Promise<void> {
        console.log('[RealDrone] 调用 SDK: controlPayload', params);
      }

      async getPosition(): Promise<{ latitude: number; longitude: number; altitude: number }> {
        // TODO: 从 DJI SDK 获取真实位置
        return { latitude: 0, longitude: 0, altitude: 0 };
      }

      async getBattery(): Promise<number> {
        // TODO: 从 DJI SDK 获取电量
        return 100;
      }
    }

    this.adapter = new RealDroneAdapter();

    this.flightController = new FlightController(this.adapter, {
      droneId: this.config.droneId,
    });

    console.log('[Init] 真实无人机适配器已创建');
    console.log('[Init] 注意: 需要 DJI SDK 授权才能控制真实无人机');
  }

  /**
   * 初始化视频转发
   */
  private initVideoRelay(): void {
    this.videoRelay = new VideoRelay({
      relayPort: this.config.videoPort,
    });

    this.videoRelay.start().catch(console.error);
  }

  /**
   * 起飞
   */
  async takeoff(): Promise<void> {
    if (this.adapter) {
      await this.adapter.takeoff();
    }
  }

  /**
   * 降落
   */
  async land(): Promise<void> {
    if (this.adapter) {
      await this.adapter.land();
    }
  }

  /**
   * 获取状态
   */
  getStatus(): any {
    return {
      mode: this.config.mode,
      droneId: this.config.droneId,
      simulator: this.simulator?.getState() || null,
      videoRelay: this.videoRelay?.getStatus() || null,
      flightController: this.flightController?.getFlightState() || null,
    };
  }

  /**
   * 停止
   */
  async stop(): Promise<void> {
    console.log('[DroneIntegration] 正在停止...');

    if (this.flightController) {
      await this.flightController.stopMission();
    }

    if (this.videoRelay) {
      this.videoRelay.stop();
    }

    if (this.simulator) {
      this.simulator.stop();
    }

    console.log('[DroneIntegration] 已停止');
  }
}

// 主函数
async function main() {
  const mode = process.argv.includes('--simulator') ? 'simulator' : 'real';

  const integration = new DroneIntegration({ mode });

  // 处理进程退出
  process.on('SIGINT', async () => {
    await integration.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    await integration.stop();
    process.exit(0);
  });

  await integration.init();

  console.log('\n[Main] 无人机集成模块已启动');
  console.log('[Main] 状态查询: GET /status');
  console.log('[Main] 控制命令: POST /command');
}

// 导出
export { DroneIntegration, DroneIntegrationConfig };

// 运行
if (require.main === module) {
  main().catch(console.error);
}
