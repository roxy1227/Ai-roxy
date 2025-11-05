from __future__ import annotations

import threading

import numpy as np


class SharedFrame:
    """共享最新一帧叠框图像与检测框（简化为单槽，追求最新值）。"""

    def __init__(self, width: int = 640, height: int = 640) -> None:
        self.width = width
        self.height = height
        self._lock = threading.Lock()
        self._image: np.ndarray | None = None
        self._boxes: list[tuple[int, int, int, int]] = []

    def write(self, image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> None:
        if image is None:
            return
        with self._lock:
            self._image = image
            self._boxes = boxes

    def read(self) -> tuple[np.ndarray | None, list[tuple[int, int, int, int]]]:
        with self._lock:
            return self._image, list(self._boxes)
