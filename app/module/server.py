from __future__ import annotations

import multiprocessing as mp
import tkinter as tk
from tkinter import filedialog
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from module import config as config_mod
from module.dpi import setup_dpi_awareness
from module.process_manager import ProcessManager


def ok(msg: str, data: object | None = None) -> JSONResponse:
    return JSONResponse({"error": 0, "msg": msg, "data": data})


def err(msg: str, data: object | None = None) -> JSONResponse:
    return JSONResponse({"error": 1, "msg": msg, "data": data})


def _hotkey_listener_process(result_queue: mp.Queue) -> None:
    """独立进程监听按键"""
    try:
        from pynput import mouse
        
        hotkey_pressed = None
        
        def on_click(x, y, button, pressed):
            nonlocal hotkey_pressed
            if pressed:  # 只在按下时记录
                hotkey_pressed = button
                # 停止监听器
                mouse_listener.stop()
            return None
        
        # 只启动鼠标监听器
        mouse_listener = mouse.Listener(on_click=on_click)
        mouse_listener.start()
        
        # 等待按键按下
        mouse_listener.join()
        
        # 处理结果
        if hotkey_pressed:
            if isinstance(hotkey_pressed, mouse.Button):
                result = hotkey_pressed.name
            else:
                result = str(hotkey_pressed)
            
            result_queue.put(result)
        else:
            result_queue.put(None)
            
    except Exception as e:
        result_queue.put(f"error: {str(e)}")


def _file_dialog_process(result_queue: mp.Queue) -> None:
    """独立进程打开文件选择对话框"""
    try:
        # 隐藏主窗口
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', True)
        
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[
                ("模型文件", "*.pt *.pth *.onnx *.engine *. weights"),
                ("所有文件", "*.*")
            ]
        )
        
        # 销毁窗口
        root.destroy()
        
        # 返回结果
        if file_path:
            result_queue.put(file_path)
        else:
            result_queue.put(None)
    except Exception as e:
        result_queue.put(f"error: {str(e)}")


def create_app() -> FastAPI:
    # 确保工厂模式下也执行一次 DPI 感知（Windows 环境）
    setup_dpi_awareness()
    app = FastAPI()

    # CORS: 默认放开，若需严格来源可改为从配置读取
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    cfg = config_mod.ConfigManager()
    pm = ProcessManager(cfg)

    @app.post("/start_detect")
    def start_detect():
        started = pm.start_detect_pipeline()
        if not started:
            return err("检测已在运行或启动失败")
        return ok("检测已启动")

    @app.post("/stop_detect")
    def stop_detect():
        pm.stop_detect_pipeline()
        # stop_preview 在进程管理中被联动
        return ok("检测已停止（展示亦已联动停止，如在运行）")

    @app.post("/preview")
    def preview():
        started = pm.start_preview()
        if not started:
            return err("预览已在运行或启动失败")
        return ok("预览已启动；关闭窗口后将返回停止信息")

    @app.post("/stop_preview")
    def stop_preview():
        pm.stop_preview()
        return ok("预览已停止")

    @app.post("/config/get")
    def config_get():
        return ok("配置获取成功", cfg.read())

    @app.post("/config/set")
    def config_set(changes: dict[str, Any] | None = None):
        if not changes:
            return err("缺少配置内容")
        cfg.update(changes)
        return ok("配置已保存", cfg.read())
    
    @app.post("/hotkey/change")
    def hotkey_change():
        """启动一个独立的监听进程，直到用户按下任意按键，然后返回按键信息"""
        # 创建进程间通信队列
        result_queue = mp.Queue()
        
        # 启动监听进程
        listener_process = mp.Process(target=_hotkey_listener_process, args=(result_queue,))
        listener_process.start()
        
        # 等待进程结束并获取结果
        listener_process.join()
        
        # 获取按键结果
        try:
            hotkey = result_queue.get(timeout=1)
            if hotkey and not str(hotkey).startswith("error"):
                return ok("热键捕获成功", {"hotkey": hotkey})
            else:
                return err("热键捕获失败或被中断")
        except:
            return err("热键捕获超时或发生错误")
    
    @app.post("/model/classes")
    def model_classes(model_path: dict[str, str] | None = None):
        """从模型中获取所有类别信息"""
        if not model_path or "model_path" not in model_path:
            return err("缺少模型路径参数")
        
        path = model_path["model_path"]
        try:
            from ultralytics import YOLO
            
            # 加载模型
            model = YOLO(path)
            
            # 获取模型的类别信息
            if hasattr(model, 'names'):
                # model.names 是一个字典，键是类别ID，值是类别名称
                classes = [{"id": int(k), "name": str(v)} for k, v in model.names.items()]
                return ok("模型类别获取成功", classes)
            else:
                return err("模型不包含类别信息")
                
        except Exception as e:
            return err(f"模型加载失败: {str(e)}")
    
    @app.post("/model/get")
    def model_get():
        """打开文件选择对话框让用户选择模型文件"""
        # 创建进程间通信队列
        result_queue = mp.Queue()
        
        # 启动文件选择进程
        file_process = mp.Process(target=_file_dialog_process, args=(result_queue,))
        file_process.start()
        
        # 等待进程结束并获取结果
        file_process.join()
        
        # 获取文件路径结果
        try:
            file_path = result_queue.get(timeout=1)
            if file_path and not str(file_path).startswith("error"):
                return ok("模型文件选择成功", {"model_path": file_path})
            else:
                return err("文件选择被取消或发生错误")
        except:
            return err("文件选择超时或发生错误")

    return app