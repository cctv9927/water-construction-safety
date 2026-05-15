import React, { useState, useEffect } from 'react'
import { sandboxApi } from '../lib/api'

interface VideoPlayerProps {
  cameraId: string | null
  onCameraChange: (id: string) => void
}

export default function VideoPlayer({ cameraId, onCameraChange }: VideoPlayerProps) {
  const [cameras, setCameras] = useState<any[]>([])
  const [videos, setVideos] = useState<any[]>([])
  const [selectedVideo, setSelectedVideo] = useState<any>(null)

  useEffect(() => {
    loadCameras()
  }, [])

  useEffect(() => {
    if (cameraId) {
      loadVideos(cameraId)
    }
  }, [cameraId])

  const loadCameras = async () => {
    try {
      const data = await sandboxApi.getCameras()
      setCameras(data)
      if (data.length > 0 && !cameraId) {
        onCameraChange(data[0].camera_id)
      }
    } catch (error) {
      console.error('Failed to load cameras:', error)
    }
  }

  const loadVideos = async (id: string) => {
    try {
      const data = await sandboxApi.getVideos(id)
      setVideos(data)
    } catch (error) {
      console.error('Failed to load videos:', error)
    }
  }

  return (
    <div className="video-player">
      <div className="video-sidebar">
        <h3>📹 摄像头列表</h3>
        <div className="camera-list">
          {cameras.map(camera => (
            <button
              key={camera.camera_id}
              onClick={() => onCameraChange(camera.camera_id)}
              className={cameraId === camera.camera_id ? 'active' : ''}
            >
              {camera.camera_id}
              {camera.location && <span className="location">{camera.location}</span>}
            </button>
          ))}
        </div>

        <h4>视频片段</h4>
        <div className="video-list">
          {videos.map(video => (
            <div
              key={video.id}
              className={`video-item ${selectedVideo?.id === video.id ? 'selected' : ''}`}
              onClick={() => setSelectedVideo(video)}
            >
              {video.thumbnail_path && (
                <img src={video.thumbnail_path} alt={video.title} />
              )}
              <div className="video-info">
                <span className="video-title">{video.title || `视频 ${video.id}`}</span>
                <span className="video-duration">
                  {video.duration ? `${Math.round(video.duration)}s` : '--'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="video-main">
        {selectedVideo ? (
          <>
            <video 
              key={selectedVideo.id}
              controls 
              autoPlay 
              className="video-element"
            >
              <source src={selectedVideo.file_path} type="video/mp4" />
              您的浏览器不支持视频播放
            </video>
            <div className="video-details">
              <h3>{selectedVideo.title || `视频 ${selectedVideo.id}`}</h3>
              <p>位置: {selectedVideo.location || '未知'}</p>
              <p>时间: {selectedVideo.start_time ? new Date(selectedVideo.start_time).toLocaleString() : '--'}</p>
              {selectedVideo.detection_results?.length > 0 && (
                <div className="detection-results">
                  <h4>🎯 AI 检测结果</h4>
                  <ul>
                    {selectedVideo.detection_results.map((r: any, i: number) => (
                      <li key={i}>
                        {r.category} - 置信度: {(r.confidence * 100).toFixed(1)}%
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="video-placeholder">
            <p>👈 选择视频片段进行播放</p>
          </div>
        )}
      </div>
    </div>
  )
}
