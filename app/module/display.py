from __future__ import annotations

import time
from collections.abc import Callable

import cv2

from module.ipc import SharedFrameShm


def preview_loop(shared: SharedFrameShm, is_running: Callable[[], bool]) -> None:
    frame_count = 0
    window_name = "preview"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    while is_running():
        frame_count += 1

        # 读取共享内存
        image, _ = shared.read()

        if image is None:
            time.sleep(0.005)
            continue

        # 显示图像
        cv2.imshow(window_name, image)

        # 等待按键（非阻塞）- 每10帧检查一次以降低开销
        if frame_count % 60 == 0:  # 每10帧检查一次按键，降低 waitKey 开销
            if cv2.waitKey(1) & 0xFF == 27:  # ESC 退出
                break

    try:
        cv2.destroyWindow(window_name)
    except Exception:
        pass
