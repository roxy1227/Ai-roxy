# 接口文档（FastAPI 后端）

所有接口均为 POST，统一返回结构：

```json
{ "error": 0 | 1, "msg": "中文信息", "data": any | null }
```

基础信息

- 基础地址：`http://localhost:8000`
- Content-Type：`application/json`

接口一览

- `/start_detect` 启动检测流水线
- `/stop_detect` 停止检测（联动停止预览）
- `/preview` 启动预览窗口（ESC 关闭）
- `/stop_preview` 停止预览窗口
- `/config/get` 读取配置
- `/config/set` 修改并保存配置
- `/hotkey/change` 捕获新的热键
- `/model/classes` 获取模型类别
- `/model/get` 选择模型文件

详细说明

1. /start_detect

- 方法：POST
- 请求体：无
- 响应示例：

```json
{ "error": 0, "msg": "检测已启动", "data": null }
```

2. /stop_detect

- 方法：POST
- 请求体：无
- 行为：停止截图+推理；若预览在运行将同步停止
- 响应示例：

```json
{ "error": 0, "msg": "检测已停止（展示亦已联动停止，如在运行）", "data": null }
```

3. /preview

- 方法：POST
- 请求体：无
- 行为：启动预览窗口，从共享内存持续读取叠框图像进行显示；按 ESC 关闭窗口
- 返回：接口会立即返回启动结果；展示结束后将打印/记录停止信息
- 响应示例：

```json
{ "error": 0, "msg": "预览已启动；关闭窗口后将返回停止信息", "data": null }
```

4. /stop_preview

- 方法：POST
- 请求体：无
- 响应示例：

```json
{ "error": 0, "msg": "预览已停止", "data": null }
```

5. /config/get

- 方法：POST
- 请求体：无
- 响应 data：配置对象
- 配置字段：
  - `x_pixels` number（x 轴 360 度像素）
  - `y_pixels` number（y 轴 180 度像素）
  - `x_base_speed` number（x 轴基础速度）
  - `y_base_speed` number（y 轴基础速度）
  - `model_path` string（模型地址）
  - `hotkey` string（触发热键）
  - `x_target_offset` number（x 轴目标偏移）
  - `y_target_offset` number（y 轴目标偏移）
  - `confidence` number（置信值）
  - `classes` array（要检测的类别，数字或字符串）
  - `enable_int8` boolean（是否开启 int8）
- 响应示例：

```json
{
  "error": 0,
  "msg": "配置获取成功",
  "data": {
    "x_pixels": 1920,
    "y_pixels": 1080,
    "x_base_speed": 1.0,
    "y_base_speed": 1.0,
    "model_path": "models/yolo12n.engine",
    "hotkey": "x1",
    "x_target_offset": 0,
    "y_target_offset": 0,
    "confidence": 0.25,
    "classes": [0],
    "enable_int8": false
  }
}
```

6. /config/set

- 方法：POST
- 请求体：JSON（上述任意字段的子集）
- 示例请求：

```json
{ "confidence": 0.3, "classes": [0, 1], "model_path": "C:/models/yolo12.onnx" }
```

- 响应：成功时返回最新配置
- 响应示例：

```json
{
  "error": 0,
  "msg": "配置已保存",
  "data": {
    /* 合并后的配置 */
  }
}
```

7. /hotkey/change

- 方法：POST
- 请求体：无
- 行为：启动一个独立的监听进程，直到用户按下任意按键（键盘或鼠标），然后返回按键信息
- 响应示例：

```json
{
  "error": 0,
  "msg": "热键捕获成功",
  "data": {
    "hotkey": "f8"
  }
}
```

8. /model/classes

- 方法：POST
- 请求体：{"model_path": "模型路径"}
- 行为：从指定模型中获取所有类别信息
- 响应示例：

```json
{
  "error": 0,
  "msg": "模型类别获取成功",
  "data": [
    {"id": 0, "name": "person"},
    {"id": 1, "name": "bicycle"},
    {"id": 2, "name": "car"},
    // ... 更多类别
  ]
}
```

9. /model/get

- 方法：POST
- 请求体：无
- 行为：打开文件选择对话框让用户选择模型文件，返回选中的文件路径
- 响应示例：

```json
{
  "error": 0,
  "msg": "模型文件选择成功",
  "data": {
    "model_path": "C:/models/yolo12n.pt"
  }
}
```

错误示例

```json
{ "error": 1, "msg": "缺少配置内容", "data": null }
```

注意事项

- 所有接口为 POST；响应均包含中文 `msg` 字段
- 预览窗口运行在本机桌面环境，ESC 可关闭；停止检测会联动停止预览
- 当前推理为占位实现（中心方框），替换 yolo12 后保持同样输出（boxes 与叠框图）
- 热键监听需要安装额外依赖：`pip install pynput`

安装依赖

```bash
pip install -e .
```

```
