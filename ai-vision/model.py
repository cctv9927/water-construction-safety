"""
YOLOv8 ONNX 推理引擎
支持 YOLOv8n/s/m/l/x 模型，支持导出后的 ONNX 模型
"""
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np

logger = logging.getLogger("ai-vision.model")

# ─── COCO + 工地安全扩展类别 ─────────────────────────────
CLASS_NAMES = [
    "helmet",         # 0  安全帽（已佩戴）
    "no_helmet",      # 1  未戴安全帽
    "person",         # 2  人员
    "vehicle",        # 3  车辆/机械
    "material",       # 4  建材/物料
    "hazard",         # 5  环境安全隐患
    "fire",           # 6  火灾隐患
    "unguarded_edge",  # 7  无防护边缘
]


class YOLOv8ONNX:
    """
    YOLOv8 ONNX 推理类
    支持 Ultralytics 导出的标准 ONNX 模型
    """

    def __init__(
        self,
        model_path: str = "models/yolov8n.onnx",
        conf_threshold: float = 0.5,
        max_detections: int = 100,
        input_size: int = 640,
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.max_detections = max_detections
        self.input_size = input_size

        # 延迟导入 onnxruntime（可选依赖）
        self._ort = None
        self._session = None
        self._providers = None
        self._load_model()

        self.num_classes = len(CLASS_NAMES)
        self.class_names = CLASS_NAMES

    def _load_model(self):
        """加载 ONNX 模型"""
        try:
            import onnxruntime as ort
            self._ort = ort
            self._providers = ort.get_available_providers()
            logger.info(f"可用 ONNX Runtime providers: {self._providers}")

            # 优先使用 GPU
            provider = "CUDAExecutionProvider" if "CUDAExecutionProvider" in self._providers else "CPUExecutionProvider"
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=[provider],
            )
            logger.info(f"ONNX 模型加载成功: {self.model_path}, provider: {provider}")

            # 读取输入输出名称
            self._input_name = self._session.get_inputs()[0].name
            self._output_names = [o.name for o in self._session.get_outputs()]
            logger.info(f"输入名: {self._input_name}, 输出名: {self._output_names}")

        except ImportError:
            logger.warning("onnxruntime 未安装，将使用 ultralytics 直接推理（需要 PyTorch）")
            self._session = None
        except Exception as e:
            logger.error(f"ONNX 模型加载失败: {e}")
            raise

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        图像预处理
        1. 缩放至 input_size
        2. 归一化 BGR→RGB
        3. HWC→CHW + 归一化
        """
        h, w = img.shape[:2]
        scale = self.input_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = np.array(
            Image.fromarray(img).resize((new_w, new_h), Image.BILINEAR)
        )

        # 填充为正方形
        canvas = np.zeros((self.input_size, self.input_size, 3), dtype=np.uint8)
        canvas[:new_h, :new_w] = resized
        self._pad = (new_h, new_w, scale)

        # HWC -> CHW, normalize
        blob = canvas.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))  # CHW
        blob = np.expand_dims(blob, axis=0)     # NCHW
        return blob

    def _postprocess(
        self,
        outputs: np.ndarray,
        original_shape: tuple,
    ) -> List[Dict[str, Any]]:
        """
        后处理：解析 YOLOv8 输出，NMS，返回检测结果
        YOLOv8 输出格式: (1, 84, 8400) — 84 = 4(bbox) + 80(classes)
        """
        predictions = outputs[0]  # (84, 8400)
        if predictions.shape[0] != 84:
            # 非标准格式，降级返回
            logger.warning(f"未识别的输出形状: {predictions.shape}")
            return []

        # 解析
        bboxes = predictions[:4, :].T        # (8400, 4) x,y,w,h
        scores = predictions[4:, :].T        # (8400, 80) class scores

        # 转为 (N, 4) 列表
        orig_h, orig_w = original_shape[:2]
        new_h, new_w, scale = self._pad

        results: List[Dict[str, Any]] = []

        for i in range(scores.shape[0]):
            cls_scores = scores[i]
            cls_id = int(np.argmax(cls_scores))
            conf = float(cls_scores[cls_id])

            if conf < self.conf_threshold:
                continue
            if cls_id >= len(CLASS_NAMES):
                continue

            # 反归一化 bbox
            x, y, w, h = bboxes[i]
            x = max(0, int((x - (self.input_size - new_w) / 2) / scale))
            y = max(0, int((y - (self.input_size - new_h) / 2) / scale))
            bw = min(orig_w, int(w / scale))
            bh = min(orig_h, int(h / scale))

            x1, y1 = x, y
            x2, y2 = x + bw, y + bh

            results.append({
                "class_id": cls_id,
                "class_name": CLASS_NAMES[cls_id],
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            })

            if len(results) >= self.max_detections:
                break

        # 简单 NMS
        results = self._nms(results)
        return results

    def _nms(self, boxes: List[Dict], iou_thresh: float = 0.45) -> List[Dict]:
        """简单 NMS"""
        if not boxes:
            return []
        boxes.sort(key=lambda x: x["confidence"], reverse=True)
        keep = []
        while boxes:
            best = boxes.pop(0)
            keep.append(best)
            boxes = [
                b for b in boxes
                if self._iou(best["bbox"], b["bbox"]) < iou_thresh
                or b["class_id"] != best["class_id"]
            ]
        return keep

    @staticmethod
    def _iou(a: List, b: List) -> float:
        """计算 IOU"""
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        return inter / (area_a + area_b - inter + 1e-6)

    def detect(
        self,
        img: np.ndarray,
        conf_threshold: Optional[float] = None,
        max_detections: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """主检测接口"""
        conf_threshold = conf_threshold or self.conf_threshold
        max_detections = max_detections or self.max_detections

        blob = self._preprocess(img)

        if self._session is not None:
            # ONNX Runtime 推理
            outputs = self._session.run(
                self._output_names,
                {self._input_name: blob.astype(np.float32)},
            )
            results = self._postprocess(outputs[0], img.shape)
        else:
            # 降级：使用 ultralytics（需要安装 torch）
            results = self._detect_ultralytics(img, conf_threshold)

        # 截断
        return results[:max_detections]

    def _detect_ultralytics(
        self,
        img: np.ndarray,
        conf_threshold: float,
    ):
        """使用 ultralytics YOLO 推理（备选）"""
        from ultralytics import YOLO
        model_file = self.model_path.replace(".onnx", ".pt")
        if not Path(model_file).exists():
            model_file = "yolov8n.pt"
        yolo = YOLO(model_file)
        results = yolo(img, conf=conf_threshold, verbose=False)
        out = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                out.append({
                    "class_id": cls_id,
                    "class_name": CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}",
                    "confidence": float(box.conf[0]),
                    "bbox": [int(x) for x in box.xyxy[0].tolist()],
                })
        return out
