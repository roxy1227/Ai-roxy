chcp 65001 >nul

powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"


@echo 安装成功
pause