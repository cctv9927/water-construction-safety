/**
 * 视频流转发模块 - 处理无人机视频流
 */

import WebSocket from 'ws';

// 视频帧类型
interface VideoFrame {
  timestamp: number;
  data: Buffer;
  width: number;
  height: number;
  format: string;
}

// 视频流状态
interface VideoStreamState {
  active: boolean;
  startTime: number;
  frameCount: number;
  bitrate: number;
  resolution: string;
}

// 视频流配置
interface VideoRelayConfig {
  inputWsUrl: string;    // 无人机视频流 WebSocket URL
  outputWsUrl: string;   // 转发目标 WebSocket URL
  relayPort: number;      // 本地中转端口
  maxBufferSize: number; // 最大缓冲帧数
  enableRecord: boolean; // 是否启用录制
  outputDir: string;     // 录制输出目录
}

/**
 * 视频流转发器
 * 从无人机接收视频流，处理后转发到指定目标
 */
export class VideoRelay {
  private config: VideoRelayConfig;
  private inputWs: WebSocket | null = null;
  private outputWs: WebSocket | null = null;
  private localServer: WebSocket.Server | null = null;
  private clients: Set<WebSocket> = new Set();
  private state: VideoStreamState;
  private frameBuffer: VideoFrame[] = [];
  private statsInterval: NodeJS.Timeout | null = null;

  constructor(config: Partial<VideoRelayConfig> = {}) {
    this.config = {
      inputWsUrl: config.inputWsUrl || 'ws://localhost:8083/video',
      outputWsUrl: config.outputWsUrl || 'ws://localhost:8081/ws/drone',
      relayPort: config.relayPort || 8084,
      maxBufferSize: config.maxBufferSize || 30,
      enableRecord: config.enableRecord ?? false,
      outputDir: config.outputDir || '/tmp/drone-recordings',
    };

    this.state = {
      active: false,
      startTime: 0,
      frameCount: 0,
      bitrate: 0,
      resolution: '1920x1080',
    };
  }

  /**
   * 启动视频流转发
   */
  async start(): Promise<void> {
    console.log('[VideoRelay] 启动视频流转发服务...');

    // 创建本地 WebSocket 服务器，供前端订阅
    this.localServer = new WebSocket.Server({ port: this.config.relayPort });

    this.localServer.on('connection', (ws) => {
      console.log('[VideoRelay] 前端客户端连接');
      this.clients.add(ws);

      // 发送当前状态
      ws.send(JSON.stringify({
        type: 'stream_status',
        data: this.getStatus()
      }));

      // 发送最近的缓冲帧
      this.frameBuffer.forEach((frame) => {
        ws.send(JSON.stringify({
          type: 'video_frame',
          data: {
            timestamp: frame.timestamp,
            size: frame.data.length,
            width: frame.width,
            height: frame.height,
            format: frame.format
          }
        }));
      });

      ws.on('close', () => {
        console.log('[VideoRelay] 前端客户端断开');
        this.clients.delete(ws);
      });
    });

    // 连接到无人机视频源
    this.connectToDrone();

    // 启动统计
    this.startStats();

    console.log(`[VideoRelay] 本地端口: ${this.config.relayPort}`);
    console.log('[VideoRelay] 启动完成');
  }

  /**
   * 连接到无人机视频源
   */
  private connectToDrone(): void {
    console.log(`[VideoRelay] 连接无人机视频源: ${this.config.inputWsUrl}`);

    try {
      this.inputWs = new WebSocket(this.config.inputWsUrl);

      this.inputWs.on('open', () => {
        console.log('[VideoRelay] 已连接到无人机视频源');
        this.state.active = true;
        this.state.startTime = Date.now();
      });

      this.inputWs.on('message', (data) => {
        this.handleVideoFrame(data as Buffer);
      });

      this.inputWs.on('close', () => {
        console.log('[VideoRelay] 与无人机视频源断开连接');
        this.state.active = false;
        // 尝试重连
        setTimeout(() => this.connectToDrone(), 5000);
      });

      this.inputWs.on('error', (err) => {
        console.error('[VideoRelay] 视频源连接错误:', err.message);
      });
    } catch (err) {
      console.error('[VideoRelay] 无法连接到视频源:', err);
      setTimeout(() => this.connectToDrone(), 5000);
    }
  }

  /**
   * 处理视频帧
   */
  private handleVideoFrame(data: Buffer): void {
    this.state.frameCount++;

    // 解析帧（简化：实际需要根据具体协议解析）
    const frame: VideoFrame = {
      timestamp: Date.now(),
      data: data,
      width: 1920,
      height: 1080,
      format: 'h264'
    };

    // 添加到缓冲区
    this.frameBuffer.push(frame);
    if (this.frameBuffer.length > this.config.maxBufferSize) {
      this.frameBuffer.shift();
    }

    // 转发到所有客户端
    this.broadcastToClients({
      type: 'video_frame',
      data: {
        timestamp: frame.timestamp,
        size: frame.data.length,
        width: frame.width,
        height: frame.height,
        format: frame.format
      }
    });

    // 如果配置了转发目标，也转发
    if (this.outputWs && this.outputWs.readyState === WebSocket.OPEN) {
      this.outputWs.send(data);
    }
  }

  /**
   * 广播到所有本地客户端
   */
  private broadcastToClients(message: any): void {
    const data = JSON.stringify(message);
    this.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(data);
      }
    });
  }

  /**
   * 转发到外部目标
   */
  async forwardTo(url: string): Promise<void> {
    console.log(`[VideoRelay] 转发到: ${url}`);

    return new Promise((resolve, reject) => {
      this.outputWs = new WebSocket(url);

      this.outputWs.on('open', () => {
        console.log('[VideoRelay] 已连接到转发目标');
        resolve();
      });

      this.outputWs.on('error', (err) => {
        console.error('[VideoRelay] 转发目标连接错误:', err.message);
        reject(err);
      });
    });
  }

  /**
   * 启动统计
   */
  private startStats(): void {
    let lastFrameCount = 0;

    this.statsInterval = setInterval(() => {
      const now = Date.now();
      const elapsed = (now - this.state.startTime) / 1000;
      const framesDiff = this.state.frameCount - lastFrameCount;

      this.state.bitrate = Math.round((framesDiff * 8) / elapsed);

      this.broadcastToClients({
        type: 'stream_stats',
        data: this.getStats()
      });

      lastFrameCount = this.state.frameCount;
    }, 1000);
  }

  /**
   * 获取状态
   */
  getStatus(): VideoStreamState {
    return { ...this.state };
  }

  /**
   * 获取统计
   */
  getStats(): any {
    const elapsed = (Date.now() - this.state.startTime) / 1000;
    return {
      active: this.state.active,
      uptime: elapsed,
      frameCount: this.state.frameCount,
      fps: this.state.frameCount / elapsed,
      bitrate: this.state.bitrate,
      resolution: this.state.resolution,
      clients: this.clients.size,
      bufferSize: this.frameBuffer.length
    };
  }

  /**
   * 停止服务
   */
  stop(): void {
    console.log('[VideoRelay] 正在停止...');

    if (this.statsInterval) {
      clearInterval(this.statsInterval);
    }

    if (this.inputWs) {
      this.inputWs.close();
    }

    if (this.outputWs) {
      this.outputWs.close();
    }

    if (this.localServer) {
      this.localServer.close();
    }

    this.clients.forEach((client) => client.close());
    this.clients.clear();

    console.log('[VideoRelay] 已停止');
  }
}

export { VideoRelay, VideoRelayConfig, VideoStreamState, VideoFrame };
