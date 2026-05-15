import React, { useState } from 'react'
import QA from './pages/QA'
import FormGenerator from './pages/FormGenerator'
import FormFiller from './pages/FormFiller'

function App() {
  const [activeView, setActiveView] = useState<'qa' | 'generator' | 'filler'>('qa')

  return (
    <div className="app">
      <header className="header">
        <h1>📚 水利工地安全监管 - 专家系统</h1>
        <nav>
          <button 
            onClick={() => setActiveView('qa')}
            className={activeView === 'qa' ? 'active' : ''}
          >
            知识问答
          </button>
          <button 
            onClick={() => setActiveView('generator')}
            className={activeView === 'generator' ? 'active' : ''}
          >
            表格生成
          </button>
          <button 
            onClick={() => setActiveView('filler')}
            className={activeView === 'filler' ? 'active' : ''}
          >
            智慧填报
          </button>
        </nav>
      </header>

      <main className="main">
        {activeView === 'qa' && <QA />}
        {activeView === 'generator' && <FormGenerator />}
        {activeView === 'filler' && <FormFiller />}
      </main>
    </div>
  )
}

export default App
