from __future__ import annotations

from multiprocessing import shared_memory

import numpy as np


class SharedFrameShm:
    """基于 shared_memory 的高性能共享帧。

    结构：
    - 图像缓冲（BGR，uint8），固定 640x640x3 字节
    - 元信息缓冲（int32）：[seq, count] + boxes(int32) [max_boxes,4]
    """

    IMG_W = 640
    IMG_H = 640
    IMG_C = 3
    IMG_SIZE = IMG_W * IMG_H * IMG_C

    MAX_BOXES = 256
    META_HEADER_INT32 = 2  # seq, count
    META_INTS = META_HEADER_INT32 + MAX_BOXES * 4
    META_SIZE = META_INTS * 4

    def __init__(
        self,
        img_name: str | None = None,
        meta_name: str | None = None,
        create: bool = False,
    ) -> None:
        if create:
            self.shm_img = shared_memory.SharedMemory(create=True, size=self.IMG_SIZE)
            self.shm_meta = shared_memory.SharedMemory(create=True, size=self.META_SIZE)
        else:
            if img_name is None or meta_name is None:
                raise ValueError("img_name and meta_name required when create=False")
            self.shm_img = shared_memory.SharedMemory(name=img_name)
            self.shm_meta = shared_memory.SharedMemory(name=meta_name)

        self.img = np.ndarray(
            (self.IMG_H, self.IMG_W, self.IMG_C), dtype=np.uint8, buffer=self.shm_img.buf
        )
        self.meta = np.ndarray((self.META_INTS,), dtype=np.int32, buffer=self.shm_meta.buf)

    @property
    def names(self) -> tuple[str, str]:
        return self.shm_img.name, self.shm_meta.name

    def write(self, image_bgr: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> None:
        # 简单一致性策略：写入前后递增 seq，读侧读到相同 seq 视为一致
        seq = int(self.meta[0])
        self.meta[0] = seq + 1

        h, w = image_bgr.shape[:2]
        if h != self.IMG_H or w != self.IMG_W:
            resized = image_bgr
            if image_bgr.flags.c_contiguous is False:
                resized = np.ascontiguousarray(image_bgr)
            if resized.shape != (self.IMG_H, self.IMG_W, self.IMG_C):
                # 尽量避免 resize 的开销；调用方应保障尺寸一致
                resized = resized[: self.IMG_H, : self.IMG_W, : self.IMG_C]
            self.img[:, :, :] = resized
        else:
            self.img[:, :, :] = image_bgr

        count = min(len(boxes), self.MAX_BOXES)
        self.meta[1] = count
        if count:
            flat = np.fromiter(
                (c for b in boxes[:count] for c in b), dtype=np.int32, count=count * 4
            )
            self.meta[self.META_HEADER_INT32 : self.META_HEADER_INT32 + count * 4] = flat

        # 清理多余区
        remain = (self.MAX_BOXES - count) * 4
        if remain > 0:
            self.meta[
                self.META_HEADER_INT32 + count * 4 : self.META_HEADER_INT32 + count * 4 + remain
            ] = 0

        self.meta[0] = self.meta[0] + 1

    def read(self) -> tuple[np.ndarray, list[tuple[int, int, int, int]]]:
        # 双读 seq，提升一致性概率（最多重试3次避免死循环）
        max_retries = 3
        for _ in range(max_retries):
            pre = int(self.meta[0])
            cnt = int(self.meta[1])
            cnt = max(0, min(cnt, self.MAX_BOXES))
            if cnt:
                data = self.meta[self.META_HEADER_INT32 : self.META_HEADER_INT32 + cnt * 4]
                boxes = [tuple(map(int, data[i : i + 4])) for i in range(0, cnt * 4, 4)]
            else:
                boxes = []
            # 使用 np.copy() 确保连续内存，但避免不必要的拷贝开销
            img = np.ascontiguousarray(self.img)
            post = int(self.meta[0])
            if pre == post:
                return img, boxes
        # 如果重试失败，返回最后一次读取的结果
        return img, boxes

    def close(self) -> None:
        self.shm_img.close()
        self.shm_meta.close()

    def unlink(self) -> None:
        try:
            self.shm_img.unlink()
        except FileNotFoundError:
            pass
        try:
            self.shm_meta.unlink()
        except FileNotFoundError:
            pass
