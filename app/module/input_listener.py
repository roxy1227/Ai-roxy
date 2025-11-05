from __future__ import annotations

import multiprocessing as mp
import time

import numpy as np

from module.ipc import SharedFrameShm
from module.mouse_control import move_relative


def _input_listener_main(
    cfg_dict: dict, img_name: str, meta_name: str, run_flag: mp.Value[bool]
) -> None:
    """
    监听用户按键输入，当按下指定热键时，计算最近目标并移动鼠标
    """
    shared = SharedFrameShm(img_name=img_name, meta_name=meta_name, create=False)
    
    # 获取配置参数
    hotkey = cfg_dict.get("hotkey", "x1")
    x_pixels = cfg_dict.get("x_pixels", 1920)  # x轴360度像素数
    y_pixels = cfg_dict.get("y_pixels", 1080)  # y轴180度像素数
    x_base_speed = cfg_dict.get("x_base_speed", 1.0)
    y_base_speed = cfg_dict.get("y_base_speed", 1.0)
    x_target_offset = cfg_dict.get("x_target_offset", 0)
    y_target_offset = cfg_dict.get("y_target_offset", 0)
    
    # 屏幕中心点 (640x640 是处理图像的尺寸)
    screen_center_x = 640 // 2
    screen_center_y = 640 // 2
    
    # 简单的按键状态跟踪，避免重复触发
    last_trigger_time = 0
    trigger_cooldown = 0  # 100ms冷却时间
    
    # 初始化 pynput
    try:
        from pynput import keyboard, mouse
        key_listener = None
        mouse_listener = None
        
        # 解析热键
        hotkey_obj = None
        is_mouse_button = False
        
        # 检查是否为鼠标按键
        if hasattr(mouse.Button, hotkey.lower()):
            # 鼠标按键
            is_mouse_button = True
            hotkey_obj = getattr(mouse.Button, hotkey.lower())
        else:
            # 键盘按键
            is_mouse_button = False
            try:
                hotkey_obj = getattr(keyboard.Key, hotkey.lower())
            except AttributeError:
                # 普通字符键
                hotkey_obj = hotkey.lower()
        
        # 按键状态
        hotkey_pressed = False
        
        def on_key_press(key):
            nonlocal hotkey_pressed
            try:
                if hasattr(key, 'char') and key.char and key.char.lower() == hotkey_obj:
                    hotkey_pressed = True
                elif key == hotkey_obj:
                    hotkey_pressed = True
            except:
                pass
        
        def on_key_release(key):
            nonlocal hotkey_pressed
            try:
                if hasattr(key, 'char') and key.char and key.char.lower() == hotkey_obj:
                    hotkey_pressed = False
                elif key == hotkey_obj:
                    hotkey_pressed = False
            except:
                pass
            
            # 按下 ESC 键退出监听
            try:
                if key == keyboard.Key.esc:
                    return False
            except:
                pass
        
        def on_click(x, y, button, pressed):
            nonlocal hotkey_pressed
            # 对于鼠标按键
            if is_mouse_button:
                if button == hotkey_obj and pressed:
                    hotkey_pressed = True
                elif button == hotkey_obj and not pressed:
                    hotkey_pressed = False
        
        # 创建监听器
        if is_mouse_button:
            # 鼠标监听
            mouse_listener = mouse.Listener(on_click=on_click)
            mouse_listener.start()
        else:
            # 键盘监听
            key_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
            key_listener.start()
            
    except ImportError:
        print("警告: 未安装 pynput 库，使用模拟模式")
        pynput_available = False
    else:
        pynput_available = True
    
    def is_hotkey_pressed() -> bool:
        """检查热键是否被按下"""
        if not pynput_available:
            # 模拟模式，每秒触发一次
            return time.time() - last_trigger_time > 1.0
        return hotkey_pressed
    
    while run_flag.value:
        # 检查是否按下热键
        if is_hotkey_pressed():
            current_time = time.time()
            # 检查冷却时间，避免重复触发
            if current_time - last_trigger_time > trigger_cooldown:
                # 从共享内存读取检测结果
                image, boxes = shared.read()
                
                if boxes:
                    # 找到距离屏幕中心最近的目标
                    closest_box = None
                    min_distance = float('inf')
                    
                    for box in boxes:
                        x1, y1, x2, y2 = box
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        # 计算到屏幕中心的距离
                        distance = np.sqrt((center_x - screen_center_x)**2 + (center_y - screen_center_y)**2)
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_box = box
                    
                    if closest_box:
                        # 计算目标中心点
                        x1, y1, x2, y2 = closest_box
                        
                        # 使用配置的偏移量计算目标点
                        target_x = x1 + (x2 - x1) * x_target_offset
                        target_y = y1 + (y2 - y1) * y_target_offset
                        
                        # 计算需要移动的距离
                        dx = target_x - screen_center_x
                        dy = target_y - screen_center_y
                        
                        # 应用基础速度和像素比例
                        # x_pixels 是 x 轴 360 度对应的像素数
                        # y_pixels 是 y 轴 180 度对应的像素数
                        move_x = dx * x_base_speed * (360 / x_pixels)
                        move_y = dy * y_base_speed * (180 / y_pixels)
                        
                        # 移动鼠标
                        move_relative(int(move_x), int(move_y))
                        
                        # 更新触发时间
                        last_trigger_time = current_time
        
        time.sleep(0.01)  # 10ms检查一次
    
    # 清理资源
    if pynput_available:
        if key_listener:
            key_listener.stop()
        if mouse_listener:
            mouse_listener.stop()


def start_listener(cfg_dict: dict, img_name: str, meta_name: str, run_flag: mp.Value[bool]) -> None:
    """
    启动输入监听进程
    """
    p = mp.Process(target=_input_listener_main, args=(cfg_dict, img_name, meta_name, run_flag))
    p.daemon = True
    p.start()
    return p


def stop_listener() -> None:
    """
    停止输入监听
    """
    return None