import React, { useState, useRef } from 'react'
import { visionApi } from '../lib/api'

// 西藏境内示例监测点
const TIBET_DETECTION_SAMPLES = [
  {
    label: '拉萨某工地',
    description: '布达拉宫附近施工区域',
    detections: [
      { category: 'person', confidence: 0.97, x1: 120, y1: 80, x2: 200, y2: 380 },
      { category: 'helmet', confidence: 0.95, x1: 125, y1: 85, x2: 195, y2: 150 },
      { category: 'vest', confidence: 0.92, x1: 130, y1: 160, x2: 190, y2: 280 }
    ]
  },
  {
    label: '日喀则某水库',
    description: '满拉水利枢纽工程',
    detections: [
      { category: 'person', confidence: 0.94, x1: 50, y1: 100, x2: 150, y2: 350 },
      { category: 'helmet', confidence: 0.91, x1: 55, y1: 105, x2: 145, y2: 165 },
      { category: 'danger', confidence: 0.88, x1: 200, y1: 200, x2: 350, y2: 320 }
    ]
  },
  {
    label: '林芝某隧道',
    description: '派墨公路多雄拉隧道',
    detections: [
      { category: 'vest', confidence: 0.96, x1: 80, y1: 120, x2: 180, y2: 340 },
      { category: 'person', confidence: 0.93, x1: 75, y1: 115, x2: 185, y2: 345 }
    ]
  },
  {
    label: '山南某大坝',
    description: '雅砻水库施工现场',
    detections: [
      { category: 'person', confidence: 0.95, x1: 200, y1: 90, x2: 310, y2: 360 },
      { category: 'helmet', confidence: 0.93, x1: 205, y1: 95, x2: 305, y2: 160 },
      { category: 'vest', confidence: 0.90, x1: 210, y1: 170, x2: 300, y2: 270 },
      { category: 'danger', confidence: 0.85, x1: 10, y1: 10, x2: 100, y2: 80 }
    ]
  }
]

export default function AIDetection() {
  const [imageUrl, setImageUrl] = useState<string>('')
  const [detections, setDetections] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [imageElement, setImageElement] = useState<HTMLImageElement | null>(null)
  const [activeSample, setActiveSample] = useState<number>(-1)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const loadSample = (index: number) => {
    const sample = TIBET_DETECTION_SAMPLES[index]
    setActiveSample(index)
    setImageUrl(`https://placehold.co/640x480/0a0f1e/00d4ff?text=${encodeURIComponent(sample.label)}`)
    setDetections(sample.detections)
    setImageElement(null)

    // 模拟加载图片后绘制
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      setImageElement(img)
      drawDetections(img, sample.detections)
    }
    img.src = `https://placehold.co/640x480/0a0f1e/00d4ff?text=${encodeURIComponent(sample.label)}`
  }

  const handleUrlSubmit = async () => {
    if (!imageUrl) return
    setLoading(true)
    setDetections([])
    setActiveSample(-1)

    try {
      const result = await visionApi.detect(imageUrl) as any
      setDetections(result.detections || [])

      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => {
        setImageElement(img)
        drawDetections(img, result.detections || [])
      }
      img.src = imageUrl
    } catch (error) {
      console.error('Detection failed:', error)
      alert('检测失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setLoading(true)
    setDetections([])
    setActiveSample(-1)

    try {
      const result = await visionApi.detectFile(file) as any
      setDetections(result.detections || [])

      const url = URL.createObjectURL(file)
      const img = new Image()
      img.onload = () => {
        setImageUrl(url)
        setImageElement(img)
        drawDetections(img, result.detections || [])
      }
      img.src = url
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const drawDetections = (img: HTMLImageElement, detectionList: any[]) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = img.width
    canvas.height = img.height
    ctx.drawImage(img, 0, 0)

    const colorMap: Record<string, string> = {
      person: '#00d4ff',
      helmet: '#4CAF50',
      vest: '#ffcc02',
      danger: '#f44336'
    }

    detectionList.forEach(d => {
      const color = colorMap[d.category] || '#00d4ff'

      // 发光效果
      ctx.shadowColor = color
      ctx.shadowBlur = 10

      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(d.x1, d.y1, d.x2 - d.x1, d.y2 - d.y1)

      ctx.shadowBlur = 0

      ctx.fillStyle = color
      const label = `${d.category} ${(d.confidence * 100).toFixed(1)}%`
      ctx.font = 'bold 16px "Microsoft YaHei", sans-serif'
      const textWidth = ctx.measureText(label).width
      ctx.fillRect(d.x1, d.y1 - 28, textWidth + 16, 26)

      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, d.x1 + 8, d.y1 - 8)
    })
  }

  return (
    <div className="ai-detection">
      <div className="detection-controls">
        <h3>🎯 AI 目标检测</h3>
        <div className="tibet-samples">
          <span className="samples-label">📍 西藏示例：</span>
          {TIBET_DETECTION_SAMPLES.map((s, i) => (
            <button
              key={i}
              className={`sample-btn ${activeSample === i ? 'active' : ''}`}
              onClick={() => loadSample(i)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="input-group">
          <input
            type="text"
            placeholder="输入图片 URL"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleUrlSubmit()}
          />
          <button onClick={handleUrlSubmit} disabled={loading}>
            {loading ? '检测中...' : '检测'}
          </button>
        </div>
        <div className="file-upload">
          <label>
            <input type="file" accept="image/*" onChange={handleFileUpload} />
            📁 上传本地图片
          </label>
        </div>
      </div>

      <div className="detection-view">
        <div className="image-container">
          {imageElement ? (
            <canvas ref={canvasRef} className="detection-canvas" />
          ) : (
            <div className="placeholder">
              <p>选择上方西藏示例或输入图片进行检测</p>
              <p className="placeholder-sub">支持工地安全监测：安全帽、反光衣、人员、危险区域</p>
            </div>
          )}
        </div>

        <div className="detection-results">
          <h4>检测结果 ({detections.length})</h4>
          {detections.length > 0 ? (
            <div className="results-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>类别</th>
                    <th>置信度</th>
                    <th>坐标</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.map((d, i) => (
                    <tr key={i}>
                      <td><span className={`cat-badge cat-${d.category}`}>{d.category}</span></td>
                      <td>
                        <div className="conf-bar-wrap">
                          <div
                            className="conf-bar"
                            style={{ width: `${(d.confidence * 100).toFixed(1)}%` }}
                          />
                          <span>{(d.confidence * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="coord-cell">
                        [{Math.round(d.x1)}, {Math.round(d.y1)}, {Math.round(d.x2)}, {Math.round(d.y2)}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="no-results">暂无检测结果</p>
          )}
        </div>
      </div>
    </div>
  )
}
