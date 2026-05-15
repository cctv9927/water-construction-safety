import React, { useState, useRef } from 'react'
import { visionApi } from '../lib/api'

export default function AIDetection() {
  const [imageUrl, setImageUrl] = useState<string>('')
  const [detections, setDetections] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [imageElement, setImageElement] = useState<HTMLImageElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const handleUrlSubmit = async () => {
    if (!imageUrl) return
    setLoading(true)
    setDetections([])
    
    try {
      const result = await visionApi.detect(imageUrl)
      setDetections(result.detections || [])
      
      // 加载图片并绘制检测框
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

    try {
      const result = await visionApi.detectFile(file)
      setDetections(result.detections || [])
      
      // 显示本地图片
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

    // 颜色映射
    const colorMap: Record<string, string> = {
      person: '#FF0000',
      helmet: '#00FF00',
      vest: '#FFFF00',
      danger: '#FF6600'
    }

    detectionList.forEach(d => {
      const color = colorMap[d.category] || '#FF00FF'
      
      // 绘制边界框
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(d.x1, d.y1, d.x2 - d.x1, d.y2 - d.y1)

      // 绘制标签背景
      ctx.fillStyle = color
      const label = `${d.category} ${(d.confidence * 100).toFixed(1)}%`
      ctx.font = '16px Arial'
      const textWidth = ctx.measureText(label).width
      ctx.fillRect(d.x1, d.y1 - 25, textWidth + 10, 25)

      // 绘制标签文字
      ctx.fillStyle = '#FFFFFF'
      ctx.fillText(label, d.x1 + 5, d.y1 - 7)
    })
  }

  return (
    <div className="ai-detection">
      <div className="detection-controls">
        <h3>🎯 AI 目标检测</h3>
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
              <p>输入图片 URL 或上传本地图片进行检测</p>
            </div>
          )}
        </div>

        <div className="detection-results">
          <h4>检测结果 ({detections.length})</h4>
          {detections.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>类别</th>
                  <th>置信度</th>
                  <th>位置</th>
                </tr>
              </thead>
              <tbody>
                {detections.map((d, i) => (
                  <tr key={i}>
                    <td>{d.category}</td>
                    <td>{(d.confidence * 100).toFixed(1)}%</td>
                    <td>[{Math.round(d.x1)}, {Math.round(d.y1)}, {Math.round(d.x2)}, {Math.round(d.y2)}]</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="no-results">暂无检测结果</p>
          )}
        </div>
      </div>
    </div>
  )
}
