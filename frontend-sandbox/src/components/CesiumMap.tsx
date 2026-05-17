import React, { useEffect, useRef, useState } from 'react'
import { sandboxApi } from '../lib/api'

interface CesiumMapProps {
  onModelClick?: (modelId: number) => void
}

// 西藏主要城市标注
const TIBET_LANDMARKS = [
  { name: '拉萨', lon: 91.1, lat: 29.65, desc: '自治区首府' },
  { name: '日喀则', lon: 88.88, lat: 29.27, desc: '第二大城市' },
  { name: '林芝', lon: 94.36, lat: 29.54, desc: '藏东重镇' },
  { name: '山南', lon: 91.77, lat: 29.23, desc: '雅砻流域' },
  { name: '那曲', lon: 92.05, lat: 31.47, desc: '藏北高原' },
  { name: '昌都', lon: 97.18, lat: 31.14, desc: '藏东门户' },
]

export default function CesiumMap({ onModelClick }: CesiumMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<any>(null)
  const [mapReady, setMapReady] = useState(false)

  useEffect(() => {
    if (!containerRef.current) return

    let destroyed = false

    import('cesium').then(async (CesiumModule) => {
      if (destroyed || !containerRef.current) return
      const Cesium = CesiumModule

      // Cesium 1.141: 使用 baseLayer: false 禁用默认底图，手动添加
      const viewer = new Cesium.Viewer(containerRef.current, {
        baseLayer: false, // 禁用默认 imagery，后续手动添加
        baseLayerPicker: false,
        geocoder: false,
        timeline: false,
        animation: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        homeButton: false,
        fullscreenButton: false,
        infoBox: false,
        selectionIndicator: false,
      })

      if (destroyed) { viewer.destroy(); return }

      // 手动添加 OpenStreetMap 底图
      const osmImagery = new Cesium.OpenStreetMapImageryProvider({
        url: 'https://tile.openstreetmap.org/'
      })
      viewer.imageryLayers.addImageryProvider(osmImagery)

      // 加载地形（Cesium 1.141: CesiumTerrainProvider.fromIonAssetId 返回 Promise）
      try {
        const terrainProvider = await Cesium.CesiumTerrainProvider.fromIonAssetId(1)
        viewer.terrainProvider = terrainProvider
      } catch (err) {
        console.warn('Terrain load failed, using ellipsoid:', err)
      }

      // 深蓝色天空背景
      viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a0f1e')

      // 添加 OSM 建筑物（异步）
      try {
        const osmBuildings = await Cesium.createOsmBuildingsAsync()
        viewer.scene.primitives.add(osmBuildings)
      } catch (err) {
        console.warn('OSM buildings load failed:', err)
      }

      // 西藏视角 (拉萨为中心: N29.65, E91.1)
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(91.1, 29.65, 80000),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-40),
          roll: 0
        },
        duration: 2
      })

      // 加载沙盘模型
      loadSandboxModels(viewer, Cesium)

      viewerRef.current = viewer
      if (!destroyed) setMapReady(true)
    }).catch(err => {
      console.error('Cesium init failed:', err)
      if (!destroyed) setMapReady(true)
    })

    return () => {
      destroyed = true
      if (viewerRef.current) {
        viewerRef.current.destroy()
        viewerRef.current = null
      }
    }
  }, [])

  const loadSandboxModels = async (viewer: any, Cesium: any) => {
    try {
      const models = await sandboxApi.getModels() as any[]
      models.forEach((model) => {
        if (model.file_path && model.center_point) {
          const position = Cesium.Cartesian3.fromDegrees(
            model.center_point.lon,
            model.center_point.lat,
            model.center_point.alt || 0
          )
          viewer.entities.add({
            id: `model-${model.id}`,
            position,
            model: { uri: model.file_path, scale: 1.0 },
            properties: { name: model.name, modelId: model.id }
          })
        }
      })
    } catch (error) {
      console.error('Failed to load sandbox models:', error)
    }
  }

  const flyToTibet = () => {
    if (!viewerRef.current) return
    import('cesium').then((CesiumModule) => {
      const Cesium = CesiumModule
      viewerRef.current.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(91.1, 29.65, 80000),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-40),
          roll: 0
        }
      })
    })
  }

  const flyToOverview = () => {
    if (!viewerRef.current) return
    import('cesium').then((CesiumModule) => {
      const Cesium = CesiumModule
      viewerRef.current.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(91.1, 29.65, 300000)
      })
    })
  }

  return (
    <div className="cesium-map">
      <div ref={containerRef} className="cesium-container" />

      <div className="map-controls">
        <button onClick={flyToTibet}>🏠 回到西藏</button>
        <button onClick={flyToOverview}>🔍 全境视图</button>
      </div>

      {/* 西藏地标标注 */}
      <div className="map-annotations">
        {TIBET_LANDMARKS.map(lm => (
          <div key={lm.name} className="map-annotation">
            <span className="annotation-dot" />
            <span className="annotation-label">{lm.name}</span>
          </div>
        ))}
      </div>

      {!mapReady && (
        <div className="map-loading">
          <span>🛰️ 加载地图数据中...</span>
        </div>
      )}
    </div>
  )
}
