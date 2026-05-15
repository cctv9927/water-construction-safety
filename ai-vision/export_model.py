"""
导出 YOLOv8 模型为 ONNX 格式
Usage: python export_model.py [--model yolov8n] [--img-size 640]
"""
import argparse
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("export")


def main():
    parser = argparse.ArgumentParser(description="导出 YOLOv8 为 ONNX")
    parser.add_argument("--model", default="yolov8n", choices=["yolov8n","yolov8s","yolov8m","yolov8l","yolov8x"],
                        help="模型大小（n=纳米/s=小/m=中/l=大/x=特大）")
    parser.add_argument("--img-size", type=int, default=640, help="输入图片尺寸")
    parser.add_argument("--half", action="store_true", help="导出 FP16 量化模型")
    parser.add_argument("--output-dir", default="models", help="输出目录")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, f"{args.model}.onnx")

    logger.info(f"正在安装/加载 ultralytics...")
    from ultralytics import YOLO

    logger.info(f"加载模型: {args.model}.pt")
    model = YOLO(f"{args.model}.pt")

    logger.info(f"导出 ONNX 到: {output_path}")
    model.export(
        format="onnx",
        imgsz=args.img_size,
        half=args.half,
        simplify=True,
        opset=12,
    )

    logger.info("导出完成！")
    logger.info(f"模型路径: {output_path}")
    logger.info(f"如需重命名: mv {args.model}.onnx {output_path}")

    # 移动文件到目标目录
    import shutil
    src = f"{args.model}.onnx"
    if os.path.exists(src) and src != output_path:
        shutil.move(src, output_path)
        logger.info(f"已移动到: {output_path}")


if __name__ == "__main__":
    main()
