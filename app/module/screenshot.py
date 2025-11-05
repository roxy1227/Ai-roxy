from __future__ import annotations

import mss
import numpy as np


class MSSGrabber:
    """长生命周期的 mss 抓取器，避免每帧创建/销毁上下文与重复计算 bbox。"""

    def __init__(self, width: int = 640, height: int = 640) -> None:
        self.width = width
        self.height = height
        self._sct = mss.mss()
        mon = self._sct.monitors[1]
        cx = mon["width"] // 2
        cy = mon["height"] // 2
        left = max(0, cx - width // 2)
        top = max(0, cy - height // 2)
        self._bbox = {"left": left, "top": top, "width": width, "height": height}

    def grab(self) -> np.ndarray:
        sct_img = self._sct.grab(self._bbox)
        img = np.frombuffer(sct_img.bgra, dtype=np.uint8).reshape((sct_img.height, sct_img.width, 4))
        bgr = img[:, :, :3].copy()
        return np.ascontiguousarray(bgr)

    def close(self) -> None:
        try:
            self._sct.close()
        except Exception:
            pass
