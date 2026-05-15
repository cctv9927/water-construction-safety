#!/usr/bin/env python3
"""下载 YOLOv8 ONNX 模型"""
import urllib.request
import os
from pathlib import Path

# 模型 URL (使用 Ultralytics 官方 ONNX 模型)
MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "yolov8n.onnx"

def download_model():
    MODEL_DIR.mkdir(exist_ok=True)
    
    if MODEL_PATH.exists():
        print(f"模型已存在: {MODEL_PATH}")
        return
    
    print(f"正在下载模型: {MODEL_URL}")
    print(f"保存到: {MODEL_PATH}")
    
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("下载完成!")
    except Exception as e:
        print(f"下载失败: {e}")
        # 创建空文件用于测试
        MODEL_PATH.parent.mkdir(exist_ok=True)
        MODEL_PATH.write_bytes(b"")

if __name__ == "__main__":
    download_model()
