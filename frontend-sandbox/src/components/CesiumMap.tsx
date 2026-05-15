import React, { useEffect, useRef } from 'react'
import { Viewer, Terrain, BingMapsImagery, createOsmBuildingsAsync, Math as CesiumMath } from '@cesium/engine'
import { sandboxApi } from '../lib/api'

interface CesiumMapProps {
  onModelClick?: (modelId: number) => void
}

export default function CesiumMap({ onModelClick }: CesiumMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Viewer | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    // 初始化 Cesium Viewer
    const viewer = new Viewer(containerRef.current, {
      imageryProvider: new BingMapsImageryProvider({
        url: 'https://dev.virtualearth.net',
        key: 'YOUR_BING_MAPS_KEY'
      }),
      baseLayerPicker: true,
      geocoder: false,
      timeline: false,
      animation: false,
      sceneModePicker: true,
      navigationHelpButton: false,
      homeButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
    })

    viewerRef.current = viewer

    // 添加地形
    viewer.terrain = new Terrain(CesiumWorldTerrain.fromVersion(CesiumWorldTerrainVersion.V1))

    // 添加 OSM 建筑物
    const osmBuildings = createOsmBuildingsAsync()
    viewer.scene.primitives.add(osmBuildings)

    // 设置初始视角（中国区域）
    viewer.camera.flyTo({
      destination: CesiumMath.fromDegrees(116.4, 39.9, 50000),
      orientation: {
        heading: CesiumMath.toRadians(0),
        pitch: CesiumMath.toRadians(-45),
        roll: 0
      }
    })

    // 加载沙盘模型
    loadSandboxModels(viewer)

    return () => {
      viewer.destroy()
    }
  }, [])

  const loadSandboxModels = async (viewer: Viewer) => {
    try {
      const models = await sandboxApi.getModels()
      
      models.forEach((model: any) => {
        if (model.file_path && model.center_point) {
          // 添加 3D 模型
          const position = CesiumMath.fromDegrees(
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

  return (
    <div className="cesium-map">
      <div ref={containerRef} className="cesium-container" />
      <div className="map-controls">
        <button onClick={() => viewerRef.current?.camera.flyHome()}>
          🏠 回到初始位置
        </button>
        <button onClick={() => {
          viewerRef.current?.camera.flyTo({
            destination: CesiumMath.fromDegrees(116.4, 39.9, 50000)
          })
        }}>
          🔍 回到中国
        </button>
      </div>
    </div>
  )
}
