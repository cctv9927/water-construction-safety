import React, { useState, useEffect } from 'react'
import { sensorApi } from '../lib/api'

interface Sensor {
  id: number
  name: string
  type: string
  location: string
  unit: string
  is_active: boolean
  last_seen: string | null
}

export default function SensorPanel() {
  const [sensors, setSensors] = useState<Sensor[]>([])
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null)
  const [sensorData, setSensorData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSensors()
  }, [])

  useEffect(() => {
    if (selectedSensor) {
      loadSensorData(selectedSensor.id)
    }
  }, [selectedSensor])

  const loadSensors = async () => {
    try {
      const data = await sensorApi.list()
      setSensors(data)
    } catch (error) {
      console.error('Failed to load sensors:', error)
    }
  }

  const loadSensorData = async (sensorId: number) => {
    setLoading(true)
    try {
      const data = await sensorApi.getData(sensorId, { limit: 100 })
      setSensorData(data)
    } catch (error) {
      console.error('Failed to load sensor data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (sensor: Sensor) => {
    if (!sensor.is_active) return '#999'
    if (!sensor.last_seen) return '#FFC107'
    
    const lastSeen = new Date(sensor.last_seen)
    const now = new Date()
    const diffMinutes = (now.getTime() - lastSeen.getTime()) / 60000
    
    if (diffMinutes < 5) return '#4CAF50'  // 绿色 - 正常
    if (diffMinutes < 30) return '#FFC107' // 黄色 - 警告
    return '#F44336'  // 红色 - 异常
  }

  const getTypeName = (type: string) => {
    const names: Record<string, string> = {
      temperature: '🌡️ 温度',
      pressure: '📊 压力',
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

  return (
    <div className="sensor-panel">
      <h3>📡 传感器监控</h3>
      
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
            <span className="sensor-name">{sensor.name}</span>
            <span className="sensor-type">{getTypeName(sensor.type)}</span>
          </div>
        ))}
      </div>

      {selectedSensor && (
        <div className="sensor-detail">
          <h4>{selectedSensor.name}</h4>
          <div className="detail-info">
            <p>类型: {getTypeName(selectedSensor.type)}</p>
            <p>位置: {selectedSensor.location || '未知'}</p>
            <p>单位: {selectedSensor.unit || '-'}</p>
            <p>状态: {selectedSensor.is_active ? '在线' : '离线'}</p>
            <p>最后活跃: {selectedSensor.last_seen 
              ? new Date(selectedSensor.last_seen).toLocaleString() 
              : '从未'}
            </p>
          </div>

          {sensorData && sensorData.stats && (
            <div className="sensor-stats">
              <h5>📊 统计数据</h5>
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
                  <span className="stat-label">数据点数</span>
                  <span className="stat-value">
                    {sensorData.stats.count}
                  </span>
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
