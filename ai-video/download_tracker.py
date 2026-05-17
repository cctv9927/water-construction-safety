#!/usr/bin/env python3
"""
ByteTrack 追踪模型下载脚本
下载预训练追踪器所需的模型文件（YOLOX/ByteTrack）
"""
import urllib.request
import os
import sys
from pathlib import Path

# ─── 配置 ────────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent / "models"
TRACKER_DIR = MODEL_DIR / "bytetrack"

# ByteTrack 模型文件（YOLOX 检测器权重，用于高置信度二次检测）
# 这里使用官方 ByteTrack 提供的轻量模型
MODELS = {
    "yolox_tiny.onnx": (
        "https://github.com/Megvii-BaseStorage/YOLOX/releases/download/0.1.0/yolox_tiny.onnx"
    ),
    "bytetrack_x_mot17.tar": (
        "https://github.com/ifzhang/ByteTrack/releases/download/v1.0/bytetrack_x_mot17.tar"
    ),
}


def download_file(url: str, dest: Path, chunk_size: int = 8192):
    """下载文件并显示进度条"""
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"正在下载: {url}")
    print(f"保存到:   {dest}")

    try:
        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100.0, downloaded / total_size * 100) if total_size > 0 else 0
            bar_len = 40
            filled = int(bar_len * percent / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB)")
            sys.stdout.flush()

        urllib.request.urlretrieve(url, dest, reporthook=reporthook)
        sys.stdout.write("\n")
        print(f"  ✓ 下载完成: {dest.name}")
        return True

    except Exception as e:
        print(f"\n  ✗ 下载失败: {e}")
        if dest.exists():
            dest.unlink()
        return False


def download_all():
    """下载所有追踪器相关模型"""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ByteTrack 模型下载工具")
    print("=" * 60)
    print(f"模型目录: {MODEL_DIR}")
    print()

    results = {}
    for name, (url,) in MODELS.items():
        dest = MODEL_DIR / name
        if dest.exists():
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"  ⏩ 已存在: {name} ({size_mb:.1f} MB) - 跳过")
            results[name] = "skipped"
            continue

        success = download_file(url, dest)
        results[name] = "ok" if success else "failed"

    print()
    print("=" * 60)
    print("下载结果汇总:")
    for name, status in results.items():
        icon = "✓" if status == "ok" else "⏩" if status == "skipped" else "✗"
        print(f"  {icon} {name}: {status}")

    failed = [k for k, v in results.items() if v == "failed"]
    if failed:
        print(f"\n警告: 以下文件下载失败: {failed}")
        print("  追踪服务仍可使用简化 IOU 追踪模式。")
    else:
        print("\n所有模型下载完成！")
        print("  启动时将自动使用 ByteTrack 真实追踪模式。")


if __name__ == "__main__":
    download_all()
