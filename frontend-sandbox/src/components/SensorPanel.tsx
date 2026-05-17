import React, { useState, useEffect } from 'react'
import { sensorApi } from '../lib/api'

interface Sensor {
  id: number
  name: string
  type: string
  location: string
  unit: string
  value: number
  is_active: boolean
  last_seen: string | null
  trend?: 'up' | 'down' | 'stable'
}

// 西藏地区真实传感器模拟数据（高原环境）
const TIBET_MOCK_SENSORS: Sensor[] = [
  {
    id: 1,
    name: '拉萨河水位站',
    type: 'water_level',
    location: '拉萨市堆龙德庆区',
    unit: 'm',
    value: 3642.15,
    is_active: true,
    last_seen: new Date(Date.now() - 120000).toISOString(),
    trend: 'stable'
  },
  {
    id: 2,
    name: '雅鲁藏布江流量站',
    type: 'flow',
    location: '山南市乃东区',
    unit: 'm³/s',
    value: 1850.6,
    is_active: true,
    last_seen: new Date(Date.now() - 60000).toISOString(),
    trend: 'up'
  },
  {
    id: 3,
    name: '羊卓雍湖水位',
    type: 'water_level',
    location: '山南市浪卡子县',
    unit: 'm',
    value: 4441.82,
    is_active: true,
    last_seen: new Date(Date.now() - 180000).toISOString(),
    trend: 'down'
  },
  {
    id: 4,
    name: '日喀则雨量站',
    type: 'rainfall',
    location: '日喀则市桑珠孜区',
    unit: 'mm/h',
    value: 2.3,
    is_active: true,
    last_seen: new Date(Date.now() - 90000).toISOString(),
    trend: 'up'
  },
  {
    id: 5,
    name: '纳木错气象站-温度',
    type: 'temperature',
    location: '拉萨市当雄县',
    unit: '°C',
    value: 8.4,
    is_active: true,
    last_seen: new Date(Date.now() - 30000).toISOString(),
    trend: 'down'
  },
  {
    id: 6,
    name: '纳木错气象站-湿度',
    type: 'humidity',
    location: '拉萨市当雄县',
    unit: '%RH',
    value: 38.5,
    is_active: true,
    last_seen: new Date(Date.now() - 30000).toISOString(),
    trend: 'stable'
  },
  {
    id: 7,
    name: '林芝温湿度站',
    type: 'temperature',
    location: '林芝市巴宜区',
    unit: '°C',
    value: 15.7,
    is_active: true,
    last_seen: new Date(Date.now() - 60000).toISOString(),
    trend: 'stable'
  },
  {
    id: 8,
    name: '昌都风速站',
    type: 'wind_speed',
    location: '昌都市卡若区',
    unit: 'm/s',
    value: 6.2,
    is_active: true,
    last_seen: new Date(Date.now() - 45000).toISOString(),
    trend: 'up'
  },
  {
    id: 9,
    name: '那曲气压站',
    type: 'pressure',
    location: '那曲市色尼区',
    unit: 'hPa',
    value: 647.3,
    is_active: true,
    last_seen: new Date(Date.now() - 120000).toISOString(),
    trend: 'stable'
  },
  {
    id: 10,
    name: '施工坝区位移监测',
    type: 'displacement',
    location: '日喀则市南木林县',
    unit: 'mm',
    value: 1.23,
    is_active: true,
    last_seen: new Date(Date.now() - 300000).toISOString(),
    trend: 'stable'
  },
]

export default function SensorPanel() {
  const [sensors, setSensors] = useState<Sensor[]>([])
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null)
  const [sensorData, setSensorData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // 优先使用 API 数据，否则使用西藏模拟数据
    loadSensors()
  }, [])

  useEffect(() => {
    if (selectedSensor) {
      loadSensorData(selectedSensor.id)
    }
  }, [selectedSensor])

  const loadSensors = async () => {
    try {
      const data = await sensorApi.list() as Sensor[]
      if (data && data.length > 0) {
        setSensors(data)
      } else {
        setSensors(TIBET_MOCK_SENSORS)
      }
    } catch {
      // API 不可用时使用西藏模拟数据
      setSensors(TIBET_MOCK_SENSORS)
    }
  }

  const loadSensorData = async (sensorId: number) => {
    setLoading(true)
    try {
      const data = await sensorApi.getData(sensorId, { limit: 100 }) as any
      setSensorData(data)
    } catch {
      // 模拟统计
      const sensor = sensors.find(s => s.id === sensorId)
      if (sensor) {
        const base = sensor.value
        setSensorData({
          stats: {
            min: base * 0.85,
            max: base * 1.15,
            avg: base * 0.98,
            count: 120
          },
          series: Array.from({ length: 24 }, (_, i) => ({
            time: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
            value: base * (0.9 + Math.random() * 0.2)
          }))
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (sensor: Sensor) => {
    if (!sensor.is_active) return '#4a5568'
    if (!sensor.last_seen) return '#ffc107'

    const lastSeen = new Date(sensor.last_seen)
    const now = new Date()
    const diffMinutes = (now.getTime() - lastSeen.getTime()) / 60000

    if (diffMinutes < 5) return '#00d4ff'   // 蓝色 - 正常（高原蓝）
    if (diffMinutes < 30) return '#ffc107'  // 黄色 - 警告
    return '#f44336'                        // 红色 - 异常
  }

  const getTrendIcon = (trend?: string) => {
    if (trend === 'up') return '↑'
    if (trend === 'down') return '↓'
    return '→'
  }

  const getTrendColor = (trend?: string) => {
    if (trend === 'up') return '#f44336'
    if (trend === 'down') return '#4CAF50'
    return '#00d4ff'
  }

  const getTypeName = (type: string) => {
    const names: Record<string, string> = {
      temperature: '🌡️ 温度',
      pressure: '📊 气压',
      vibration: '📳 振动',
      displacement: '📏 位移',
      flow: '🌊 流量',
      wind_speed: '💨 风速',
      rainfall: '🌧️ 降雨量',
      humidity: '💧 湿度',
      water_level: '📈 水位'
    }
    return names[type] || type
  }

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      water_level: '#00d4ff',
      flow: '#0066ff',
      rainfall: '#00bfff',
      temperature: '#ff6b35',
      humidity: '#4fc3f7',
      wind_speed: '#80deea',
      pressure: '#b39ddb',
      displacement: '#ffcc02',
      vibration: '#f44336'
    }
    return colors[type] || '#00d4ff'
  }

  return (
    <div className="sensor-panel">
      <h3>📡 传感器监控</h3>
      <div className="sensor-location-tag">📍 西藏自治区</div>

      <div className="sensor-list">
        {sensors.map(sensor => (
          <div
            key={sensor.id}
            className={`sensor-item ${selectedSensor?.id === sensor.id ? 'selected' : ''}`}
            onClick={() => setSelectedSensor(sensor)}
          >
            <span
              className="status-dot"
              style={{ backgroundColor: getStatusColor(sensor) }}
            />
            <div className="sensor-info">
              <span className="sensor-name">{sensor.name}</span>
              <span className="sensor-location">{sensor.location}</span>
            </div>
            <div className="sensor-value-group">
              <span
                className="sensor-value"
                style={{ color: getTypeColor(sensor.type) }}
              >
                {sensor.type === 'temperature' || sensor.type === 'humidity'
                  ? sensor.value.toFixed(1)
                  : sensor.type === 'displacement'
                  ? sensor.value.toFixed(2)
                  : sensor.value.toFixed(1)}
              </span>
              <span className="sensor-unit">{sensor.unit}</span>
              <span
                className="sensor-trend"
                style={{ color: getTrendColor(sensor.trend) }}
              >
                {getTrendIcon(sensor.trend)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {selectedSensor && (
        <div className="sensor-detail">
          <h4>{selectedSensor.name}</h4>
          <div
            className="detail-type-badge"
            style={{ borderColor: getTypeColor(selectedSensor.type), color: getTypeColor(selectedSensor.type) }}
          >
            {getTypeName(selectedSensor.type)}
          </div>
          <div className="detail-info">
            <p><span className="detail-label">位置</span><span>{selectedSensor.location || '未知'}</span></p>
            <p><span className="detail-label">当前值</span>
              <span style={{ color: getTypeColor(selectedSensor.type) }}>
                {selectedSensor.value} {selectedSensor.unit}
              </span>
            </p>
            <p><span className="detail-label">状态</span>
              <span style={{ color: getStatusColor(selectedSensor) }}>
                {selectedSensor.is_active ? '● 在线' : '○ 离线'}
              </span>
            </p>
            <p><span className="detail-label">最后更新</span>
              <span>
                {selectedSensor.last_seen
                  ? new Date(selectedSensor.last_seen).toLocaleString()
                  : '从未'}
              </span>
            </p>
          </div>

          {sensorData && sensorData.stats && (
            <div className="sensor-stats">
              <h5>📊 统计概览</h5>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">最小值</span>
                  <span className="stat-value">
                    {sensorData.stats.min?.toFixed(2)} {selectedSensor.unit}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">最大值</span>
                  <span className="stat-value">
                    {sensorData.stats.max?.toFixed(2)} {selectedSensor.unit}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">平均值</span>
                  <span className="stat-value">
                    {sensorData.stats.avg?.toFixed(2)} {selectedSensor.unit}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">数据点</span>
                  <span className="stat-value">{sensorData.stats.count}</span>
                </div>
              </div>
            </div>
          )}

          {loading && <p className="loading">加载数据中...</p>}
        </div>
      )}
    </div>
  )
}
