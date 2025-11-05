import os
import threading
import time
import webbrowser
from pathlib import Path

import webview

from module.dpi import setup_dpi_awareness
from module.server import create_app


def start_server():
    """启动FastAPI服务"""
    setup_dpi_awareness()
    app = create_app()
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")


def main():
    index_path = 'fe/index.html'
    # 在单独的线程中启动服务
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # 等待服务启动
    time.sleep(2)
    
    # 使用pywebview创建窗口显示前端界面
    webview.create_window(
        "Ai-roxy",
        index_path,
        width=600,
        height=800,
        resizable=True
    )
    
    # 启动webview
    webview.start()


if __name__ == "__main__":
    main()