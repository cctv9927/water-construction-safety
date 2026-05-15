import { WebSocket } from 'ws'

const WS_URL = `ws://${window.location.host}/ws/alerts`

let ws: WebSocket | null = null
let reconnectTimer: NodeJS.Timeout | null = null
let messageHandler: ((data: any) => void) | null = null

export function connectWebSocket(onMessage: (data: any) => void): WebSocket {
  messageHandler = onMessage

  function connect() {
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      console.log('WebSocket connected')
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (messageHandler) {
          messageHandler(data)
        }
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...')
      reconnectTimer = setTimeout(connect, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  connect()
  return ws!
}

export function disconnectWebSocket() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
}

// API 请求封装
const API_BASE = '/api'

interface ApiOptions {
  method?: string
  body?: any
  headers?: Record<string, string>
}

export async function apiRequest<T>(
  endpoint: string, 
  options: ApiOptions = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const { method = 'GET', body, headers = {} } = options

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }

  if (body) {
    config.body = JSON.stringify(body)
  }

  const response = await fetch(url, config)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

// 沙盘相关 API
export const sandboxApi = {
  getModels: () => apiRequest('/sandbox/models'),
  getModel: (id: number) => apiRequest(`/sandbox/models/${id}`),
  getVideos: (cameraId?: string) => 
    apiRequest(`/sandbox/videos${cameraId ? `?camera_id=${cameraId}` : ''}`),
  getVideo: (id: number) => apiRequest(`/sandbox/videos/${id}`),
  getCameras: () => apiRequest('/sandbox/cameras'),
}

// 传感器相关 API
export const sensorApi = {
  list: (type?: string) => 
    apiRequest(`/sensors${type ? `?type=${type}` : ''}`),
  get: (id: number) => apiRequest(`/sensors/${id}`),
  getData: (id: number, params?: { start?: string; end?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.start) searchParams.append('start_time', params.start)
    if (params?.end) searchParams.append('end_time', params.end)
    if (params?.limit) searchParams.append('limit', String(params.limit))
    return apiRequest(`/sensors/${id}/data?${searchParams.toString()}`)
  },
}

// 视觉检测 API
export const visionApi = {
  detect: (imageData: string) => 
    apiRequest('/vision/detect', {
      method: 'POST',
      body: { image_data: imageData }
    }),
  detectFile: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`${API_BASE}/vision/detect/file`, {
      method: 'POST',
      body: formData,
    })
    return response.json()
  },
}
