import React, { useState, useEffect } from 'react'
import CesiumMap from './components/CesiumMap'
import VideoPlayer from './components/VideoPlayer'
import AIDetection from './components/AIDetection'
import SensorPanel from './components/SensorPanel'
import { connectWebSocket } from './lib/api'

function App() {
  const [activeView, setActiveView] = useState<'map' | 'video' | 'detection'>('map')
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<any[]>([])

  useEffect(() => {
    // 连接 WebSocket 接收告警
    const ws = connectWebSocket((data) => {
      if (data.type === 'alert_update') {
        setAlerts(prev => [data.data, ...prev].slice(0, 50))
      }
    })

    return () => {
      ws?.close()
    }
  }, [])

  return (
    <div className="app">
      <header className="header">
        <h1>🏗️ 水利工地安全监管 - 电子沙盘</h1>
        <nav>
          <button onClick={() => setActiveView('map')} className={activeView === 'map' ? 'active' : ''}>
            3D地图
          </button>
          <button onClick={() => setActiveView('video')} className={activeView === 'video' ? 'active' : ''}>
            视频监控
          </button>
          <button onClick={() => setActiveView('detection')} className={activeView === 'detection' ? 'active' : ''}>
            AI检测
          </button>
        </nav>
      </header>

      <main className="main">
        {activeView === 'map' && (
          <div className="map-container">
            <CesiumMap />
            <aside className="sidebar">
              <SensorPanel />
            </aside>
          </div>
        )}

        {activeView === 'video' && (
          <div className="video-container">
            <VideoPlayer 
              cameraId={selectedCamera} 
              onCameraChange={setSelectedCamera} 
            />
          </div>
        )}

        {activeView === 'detection' && (
          <div className="detection-container">
            <AIDetection />
          </div>
        )}
      </main>

      <aside className="alert-panel">
        <h3>🔔 实时告警 ({alerts.length})</h3>
        <div className="alert-list">
          {alerts.map(alert => (
            <div key={alert.id} className={`alert-item level-${alert.level}`}>
              <span className="alert-level">{alert.level}</span>
              <span className="alert-title">{alert.title}</span>
              <span className="alert-time">
                {new Date(alert.created_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </aside>
    </div>
  )
}

export default App
