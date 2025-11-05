from __future__ import annotations

import multiprocessing as mp
import time

from module.config import ConfigManager
from module.display import preview_loop
from module.inference import YoloDetector
from module.input_listener import start_listener
from module.ipc import SharedFrameShm
from module.screenshot import MSSGrabber


class ProcessManager:
    def __init__(self, cfg: ConfigManager) -> None:
        self.cfg = cfg
        self.shared = SharedFrameShm(create=True)
        self._screenshot_proc: mp.Process | None = None
        self._inference_proc: mp.Process | None = None
        self._input_listener_proc: mp.Process | None = None
        self._preview_proc: mp.Process | None = None
        self._screenshot_flag = mp.Value("b", False)
        self._inference_flag = mp.Value("b", False)
        self._input_listener_flag = mp.Value("b", False)
        self._preview_flag = mp.Value("b", False)

    def start_detect_pipeline(self) -> bool:
        # 启动截图进程
        if self._screenshot_proc and self._screenshot_proc.is_alive():
            return False
        self._screenshot_flag.value = True
        img_name, meta_name = self.shared.names
        p1 = mp.Process(
            target=_screenshot_main, args=(img_name, meta_name, self._screenshot_flag)
        )
        p1.daemon = True
        p1.start()
        self._screenshot_proc = p1
        
        # 启动推理进程
        if self._inference_proc and self._inference_proc.is_alive():
            # 如果推理进程已经在运行，只启动截图进程
            return True
        self._inference_flag.value = True
        p2 = mp.Process(
            target=_inference_main, args=(self.cfg.read(), img_name, meta_name, self._inference_flag)
        )
        p2.daemon = True
        p2.start()
        self._inference_proc = p2
        
        # 启动输入监听进程
        if not (self._input_listener_proc and self._input_listener_proc.is_alive()):
            self._input_listener_flag.value = True
            p3 = start_listener(self.cfg.read(), img_name, meta_name, self._input_listener_flag)
            self._input_listener_proc = p3
        
        return True

    def stop_detect_pipeline(self) -> None:
        # 停止截图进程
        if self._screenshot_flag:
            self._screenshot_flag.value = False
        if self._screenshot_proc:
            self._screenshot_proc.join(timeout=3)
            self._screenshot_proc = None
            
        # 停止推理进程
        if self._inference_flag:
            self._inference_flag.value = False
        if self._inference_proc:
            self._inference_proc.join(timeout=3)
            self._inference_proc = None
            
        # 停止输入监听进程
        if self._input_listener_flag:
            self._input_listener_flag.value = False
        if self._input_listener_proc:
            self._input_listener_proc = None
            
        # 联动停止预览
        self.stop_preview()

    def start_preview(self) -> bool:
        if self._preview_proc and self._preview_proc.is_alive():
            return False
        self._preview_flag.value = True
        img_name, meta_name = self.shared.names
        p = mp.Process(target=_preview_main, args=(img_name, meta_name, self._preview_flag))
        p.daemon = True
        p.start()
        self._preview_proc = p
        return True

    def stop_preview(self) -> None:
        if self._preview_flag:
            self._preview_flag.value = False
        if self._preview_proc:
            self._preview_proc.join(timeout=3)
            self._preview_proc = None


def _screenshot_main(img_name: str, meta_name: str, run_flag: mp.Value[bool]) -> None:
    shared = SharedFrameShm(img_name=img_name, meta_name=meta_name, create=False)
    grabber = MSSGrabber(640, 640)

    # 性能统计
    profile_times = {
        "grab": [],
        "write_shm": [],
        "total": [],
    }
    
    last_report_time = time.time()

    # 主循环：截图->写入共享内存
    while run_flag.value:
        loop_start = time.perf_counter()

        # 截图
        t0 = time.perf_counter()
        frame = grabber.grab()
        t_grab = time.perf_counter() - t0

        # 写共享内存
        t1 = time.perf_counter()
        shared.write(frame, [])  # 初始写入时没有检测框
        t_write = time.perf_counter() - t1

        loop_total = time.perf_counter() - loop_start

        # 性能统计
        profile_times["grab"].append(t_grab * 1000)  # ms
        profile_times["write_shm"].append(t_write * 1000)
        profile_times["total"].append(loop_total * 1000)

        # 每秒输出一次性能统计
        current_time = time.time()
        if current_time - last_report_time >= 1.0:
            print("\n=== 截图耗时（ms） ===")
            for key in ["grab", "write_shm", "total"]:
                values = profile_times[key]
                if values:
                    avg = sum(values) / len(values)
                    max_val = max(values)
                    key_name = {
                        "grab": "截图",
                        "write_shm": "写入共享内存",
                        "total": "总计"
                    }
                    print(f"{key_name[key]:12s}平均耗时={avg:6.2f}, 最大耗时={max_val:6.2f}")
            
            # 计算并输出FPS
            total_values = profile_times["total"]
            if total_values:
                fps = len(total_values) / (current_time - last_report_time)
                print(f"{'FPS':12s}: {fps:6.2f}")
            
            # 清空统计
            for key in profile_times:
                profile_times[key] = []
            
            last_report_time = current_time


def _inference_main(cfg_dict: dict, img_name: str, meta_name: str, run_flag: mp.Value[bool]) -> None:
    shared = SharedFrameShm(img_name=img_name, meta_name=meta_name, create=False)
    detector = YoloDetector(cfg_dict.get("model_path", "models/yolo12n.pt"))
    confidence = float(cfg_dict.get("confidence", 0.25))
    classes = cfg_dict.get("classes")
    enable_int8 = bool(cfg_dict.get("enable_int8", False))

    # 性能统计
    profile_times = {
        "read_shm": [],
        "inference": [],
        "write_shm": [],
        "total": [],
    }
    
    last_report_time = time.time()

    # 主循环：从共享内存读取->推理->写回共享内存
    while run_flag.value:
        loop_start = time.perf_counter()

        # 从共享内存读取图像
        t0 = time.perf_counter()
        image, _ = shared.read()
        t_read = time.perf_counter() - t0

        # 推理
        t1 = time.perf_counter()
        boxes, drawn = detector.run(
            image, confidence=confidence, classes=classes, enable_int8=enable_int8
        )
        t_inference = time.perf_counter() - t1

        # 写回共享内存（带检测框的图像和检测框数据）
        t2 = time.perf_counter()
        shared.write(drawn, boxes)
        t_write = time.perf_counter() - t2

        loop_total = time.perf_counter() - loop_start

        # 性能统计
        profile_times["read_shm"].append(t_read * 1000)  # ms
        profile_times["inference"].append(t_inference * 1000)
        profile_times["write_shm"].append(t_write * 1000)
        profile_times["total"].append(loop_total * 1000)

        # 每秒输出一次性能统计
        current_time = time.time()
        if current_time - last_report_time >= 1.0:
            print("\n=== 推理耗时（ms） ===")
            for key in ["read_shm", "inference", "write_shm", "total"]:
                values = profile_times[key]
                if values:
                    avg = sum(values) / len(values)
                    max_val = max(values)
                    key_name = {
                        "read_shm": "读取共享内存",
                        "inference": "推理",
                        "write_shm": "写入共享内存",
                        "total": "总计"
                    }
                    print(f"{key_name[key]:12s}平均耗时={avg:6.2f}, 最大耗时={max_val:6.2f}")
            
            # 计算并输出FPS
            total_values = profile_times["total"]
            if total_values:
                fps = len(total_values) / (current_time - last_report_time)
                print(f"{'FPS':12s}: {fps:6.2f}")
            
            # 清空统计
            for key in profile_times:
                profile_times[key] = []
            
            last_report_time = current_time


def _preview_main(img_name: str, meta_name: str, run_flag: mp.Value[bool]) -> None:
    shared = SharedFrameShm(img_name=img_name, meta_name=meta_name, create=False)

    def is_running() -> bool:
        return bool(run_flag.value)

    preview_loop(shared, is_running)
    run_flag.value = False