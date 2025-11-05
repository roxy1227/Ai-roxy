基于yolo的带gui简易自瞄，仅用于Windows平台

可逐步运行bat脚本来启动

如果未安装uv，则运行一下`install_uv.bat`，随后运行`init.bat`来安装依赖以及cuda的torch

运行`run.bat`即可启动程序

确保电脑中有最新版本的cuda Toolkit和cuDnn以及tensorRT（如果要启用tensorRT的话）

可用`nvidia-smi`命令来检查cuda版本

`use_trt.bat`脚本可以将`app/models/yolo12n.pt`转换为`app/models/yolo12n.engine`，如要转换自定义模型请在`app/pt_to_trt.py`中修改模型路径。