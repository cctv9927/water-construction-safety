import React, { useState, useEffect } from 'react'
import AlertList from './pages/AlertList'
import AlertDetail from './pages/AlertDetail'
import Workflow from './pages/Workflow'
import { connectWebSocket } from './lib/api'

function App() {
  const [activeView, setActiveView] = useState<'list' | 'detail' | 'workflow'>('list')
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null)
  const [alerts, setAlerts] = useState<any[]>([])

  useEffect(() => {
    const ws = connectWebSocket((data) => {
      if (data.type === 'alert_update') {
        setAlerts(prev => {
          const newAlerts = [data.data, ...prev.filter(a => a.id !== data.data.id)]
          return newAlerts.slice(0, 100)
        })
        // 刷新列表
        if (activeView === 'list') {
          // 触发列表刷新
        }
      }
    })

    return () => {
      ws?.close()
    }
  }, [activeView])

  const handleAlertClick = (alertId: number) => {
    setSelectedAlertId(alertId)
    setActiveView('detail')
  }

  const handleBack = () => {
    setSelectedAlertId(null)
    setActiveView('list')
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🚨 水利工地安全监管 - 告警工作流</h1>
        <nav>
          <button 
            onClick={() => setActiveView('list')}
            className={activeView === 'list' ? 'active' : ''}
          >
            告警列表
          </button>
          <button 
            onClick={() => setActiveView('workflow')}
            className={activeView === 'workflow' ? 'active' : ''}
          >
            工作流管理
          </button>
        </nav>
      </header>

      <main className="main">
        {activeView === 'list' && (
          <AlertList 
            onAlertClick={handleAlertClick}
            refreshKey={alerts.length}
          />
        )}
        
        {activeView === 'detail' && selectedAlertId && (
          <AlertDetail 
            alertId={selectedAlertId} 
            onBack={handleBack}
          />
        )}
        
        {activeView === 'workflow' && (
          <Workflow />
        )}
      </main>
    </div>
  )
}

export default App
