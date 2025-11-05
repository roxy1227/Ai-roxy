from __future__ import annotations

import sys


def setup_dpi_awareness() -> None:
    """在 Windows 上设置进程 DPI 感知，优先使用 pywin32。
    失败时静默忽略，避免影响服务可用性。
    """
    if sys.platform != "win32":
        return
    try:
        # pywin32: Vista+ 可用
        import win32api  # type: ignore

        win32api.SetProcessDPIAware()  # type: ignore[attr-defined]
        return
    except Exception:
        # 兼容性降级（部分环境无此 API 或未安装 pywin32）
        try:
            import ctypes

            user32 = ctypes.WinDLL("user32")
            # 尝试 SetProcessDpiAwarenessContext(-4) = PER_MONITOR_AWARE_V2
            AWARENESS_CONTEXT_PER_MONITOR_V2 = -4
            if hasattr(user32, "SetProcessDpiAwarenessContext"):
                user32.SetProcessDpiAwarenessContext(AWARENESS_CONTEXT_PER_MONITOR_V2)
            else:
                # 老接口
                if hasattr(user32, "SetProcessDPIAware"):
                    user32.SetProcessDPIAware()
        except Exception:
            # 最终静默失败
            return
