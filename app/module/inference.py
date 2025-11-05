from __future__ import annotations

import cv2
import numpy as np


class YoloDetector:
    """占位推理器：接口兼容，后续可替换为实际 yolo12 实现。

    run() 返回 (boxes, drawn)；boxes 为 (x1,y1,x2,y2) 列表。
    当前实现以极小代价在中心画一个方框，确保链路可运行。
    """

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or ""
        self._impl = None
        try:
            from ultralytics import YOLO  # type: ignore

            if self.model_path is not None:
                print(f"self.model_path: {self.model_path}")
                self._impl = YOLO(self.model_path, task="detect")
        except Exception as e:
            print(f"Error initializing YOLO: {e}")
            self._impl = None

    def run(
        self,
        image_bgr: np.ndarray,
        confidence: float = 0.25,
        classes: list[int] | list[str] | None = None,
        enable_int8: bool = False,
    ) -> tuple[list[tuple[int, int, int, int]], np.ndarray]:
        if self._impl is not None:
            params = {"conf": confidence}
            if classes:
                params["classes"] = classes

            results = self._impl.predict(source=image_bgr[:, :, ::-1], verbose=False, **params)
            boxes_list: list[tuple[int, int, int, int]] = []
            if results and len(results) > 0:
                r0 = results[0]
                if hasattr(r0, "boxes") and r0.boxes is not None:
                    xyxy = r0.boxes.xyxy.cpu().numpy().astype(int)
                    for x1, y1, x2, y2 in xyxy:
                        boxes_list.append((int(x1), int(y1), int(x2), int(y2)))
                # 使用 plot() 直接获取带检测框的图像（RGB 格式）
                drawn_rgb = r0.plot()
                # 转换为 BGR 格式
                drawn = cv2.cvtColor(drawn_rgb, cv2.COLOR_RGB2BGR)
            else:
                drawn = image_bgr.copy()
            return boxes_list, drawn

        # fallback
        h, w = image_bgr.shape[:2]
        size = min(h, w) // 4
        x1 = w // 2 - size // 2
        y1 = h // 2 - size // 2
        x2 = x1 + size
        y2 = y1 + size
        boxes = [(int(x1), int(y1), int(x2), int(y2))]
        drawn = image_bgr.copy()
        cv2.rectangle(drawn, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return boxes, drawn
