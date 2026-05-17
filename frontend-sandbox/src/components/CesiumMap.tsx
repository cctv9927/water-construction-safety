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

    import('cesium').then(async (CesiumModule) => {
      const Cesium = (CesiumModule as any).default || CesiumModule

      // 初始化 Viewer
      const viewer = new Cesium.Viewer(containerRef.current, {
        // @ts-ignore - Cesium type definitions don't match runtime API
        imageryProvider: new Cesium.BingMapsImageryProvider({
          url: 'https://dev.virtualearth.net',
          key: 'YOUR_BING_MAPS_KEY'
        }),
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
        skyBox: false,
        skyAtmosphere: false,
      } as any)

      viewerRef.current = viewer

      // 深蓝色天空背景
      try {
        ;(viewer.scene as any).backgroundColor = Cesium.Color.fromCssColorString('#0a0f1e')
      } catch {
        // ignore if not supported
      }

      // 添加地形
      try {
        const terrainProvider = await Cesium.CesiumTerrainProvider.fromIonAssetId(1)
        ;(viewer.scene as any).terrainProvider = terrainProvider
      } catch {
        // ignore if terrain unavailable
      }

      // 添加 OSM 建筑物
      try {
        const osmBuildings = await Cesium.createOsmBuildingsAsync()
        viewer.scene.primitives.add(osmBuildings)
      } catch {
        // ignore if OSM buildings unavailable
      }

      // 西藏视角 (拉萨为中心: N29.65, E91.1)
      try {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(91.1, 29.65, 80000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-40),
            roll: 0
          },
          duration: 2
        })
      } catch {
        // ignore if camera control unavailable
      }

      // 加载沙盘模型
      loadSandboxModels(viewer, Cesium)

      setMapReady(true)
    }).catch(err => {
      console.error('Cesium init failed:', err)
      setMapReady(true)
    })

    return () => {
      if (viewerRef.current) {
        viewerRef.current.destroy()
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
            model: {
              uri: model.file_path,
              scale: 1.0
            },
            properties: {
              name: model.name,
              modelId: model.id
            }
          })
        }
      })
    } catch (error) {
      console.error('Failed to load sandbox models:', error)
    }
  }

  const flyToTibet = () => {
    import('cesium').then((CesiumModule) => {
      const Cesium = (CesiumModule as any).default || CesiumModule
      if (viewerRef.current) {
        viewerRef.current.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(91.1, 29.65, 80000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-40),
            roll: 0
          }
        })
      }
    })
  }

  const flyToOverview = () => {
    import('cesium').then((CesiumModule) => {
      const Cesium = (CesiumModule as any).default || CesiumModule
      if (viewerRef.current) {
        viewerRef.current.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(91.1, 29.65, 300000)
        })
      }
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
