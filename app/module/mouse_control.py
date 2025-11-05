from __future__ import annotations

import sys


def move_relative(dx: int, dy: int) -> None:
    """使用 Windows SendInput 相对移动鼠标。其他平台为空实现。"""
    if sys.platform != "win32":
        return
    try:
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
    except Exception:
        # 退化方案：忽略错误
        pass


try:
    import win32api  # type: ignore
    import win32con  # type: ignore
except Exception:  # pragma: no cover
    # 非 Windows 或未安装 pywin32 环境兼容
    win32api = None  # type: ignore
    win32con = None  # type: ignore
