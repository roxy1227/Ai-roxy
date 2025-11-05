from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "x_pixels": 3840,  # x轴360度像素（基于4K屏幕的典型值）
    "y_pixels": 2440,  # y轴180度像素（基于4K屏幕的典型值）
    "x_base_speed": 3.0,
    "y_base_speed": 3.0,
    "model_path": "models/yolo12n.engine",
    "hotkey": "x1",  # 默认鼠标侧键1
    "x_target_offset": 0.5,
    "y_target_offset": 0.1,
    "confidence": 0.25,
    "classes": [0],
    "enable_int8": False,
}


class ConfigManager:
    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._persist_path = Path(persist_path) if persist_path else Path("config.json")
        self._lock = threading.RLock()
        self._data: dict[str, Any] = DEFAULTS.copy()
        self._load_from_disk_if_exists()

    def _load_from_disk_if_exists(self) -> None:
        if self._persist_path.exists():
            try:
                loaded = json.loads(self._persist_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except Exception:
                # 读取失败时忽略，采用默认（保持高可用）
                pass

    def read(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def update(self, changes: dict[str, Any]) -> None:
        with self._lock:
            self._data.update(changes)
            self._persist()

    def _persist(self) -> None:
        tmp = json.dumps(self._data, ensure_ascii=False, indent=2)
        self._persist_path.write_text(tmp, encoding="utf-8")