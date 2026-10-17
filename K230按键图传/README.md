# K230 按键单帧图传（手机热点版）

K230 与电脑连在同一个手机热点下，按一下 K230 上的按钮，就把**当前这一帧**图片通过 TCP 上传到电脑并保存为 JPG。

```
        手机热点（提供 DHCP + 路由）
          │                    │
       K230（服务端）      电脑（客户端）
       TCP 监听 8000       接收并保存 JPG
          │
      按下按钮 ──> 编码 JPEG ──> 上传
```

## 目录结构

```
C4K230/
├── k230_btn_snapshot_tcp.py   # K230 端：摄像头 + 按键 + 调用 wifi_snap 模块
├── libs/
│   └── wifi_snap.py           # 图传模块：联网 + TCP 服务端 + 发帧
├── pc_recv_snapshot.py        # 电脑端：连接 K230，接收并保存图片
└── received/                  # 电脑端保存的图片（自动创建）
```

板子上需要放置：

```
/sdcard/k230_btn_snapshot_tcp.py
/sdcard/libs/wifi_snap.py
```

## 使用步骤

1. **手机开热点**（建议 2.4GHz、WPA2 加密，密码 8 位以上）。
2. **K230 连上热点**：在 `k230_btn_snapshot_tcp.py` 里填好热点名称和密码。
3. **电脑连上同一个热点**。
4. **先运行 K230 的代码**，串口会打印：
   ```
   [SNAP] 连接成功，本机 IP: 10.236.192.250
   [SNAP] 已监听 10.236.192.250:8000，等待电脑连接 ...
   ```
   记下这个 IP。
5. **再运行电脑端接收代码**：
   ```
   python pc_recv_snapshot.py
   ```
   若 K230 的 IP 不是脚本里写的值，先改 `pc_recv_snapshot.py` 顶部的 `K230_IP`。
6. **按一下 K230 的按钮**，那一帧就会上传：
   - K230 串口：`[SNAP] 已发送 xxxxx 字节`
   - 电脑端：`[1] 收到 xxxxx 字节 ... -> received/snapshot_001.jpg`

> 先运行哪个其实都可以：K230 一直处于监听状态，电脑端连不上时会每 2 秒自动重试；电脑端先开也可以，等 K230 启动后自动接上。

## 配置说明

K230 端 `k230_btn_snapshot_tcp.py`：

| 变量 | 说明 |
|---|---|
| `WIFI_SSID` | 手机热点名称 |
| `WIFI_PASSWORD` | 手机热点密码 |
| `PC_PORT` | 监听端口，默认 8000，需与电脑端一致 |
| `WIDTH` / `HEIGHT` | 画面分辨率，默认 640 × 480 |

电脑端 `pc_recv_snapshot.py`：

| 变量 | 说明 |
|---|---|
| `K230_IP` | K230 串口打印的本机 IP（每次热点重新分配后可能变化） |
| `K230_PORT` | 与 K230 的 `PC_PORT` 一致 |
| `SAVE_DIR` | 图片保存目录，固定为本脚本同级的 `received/` |

## 通信协议

```
[4 字节大端长度][JPEG 数据]
```

TCP 是字节流，没有消息边界，所以每帧前面加 4 字节长度头，接收端才能正确切分。

## 模块用法（在其他程序中复用）

`libs/wifi_snap.py` 只负责网络，不碰摄像头，可在任意主程序里调用：

```python
import sys
sys.path.append("/sdcard/libs")
import wifi_snap

wifi_snap.init("热点名", "密码", 8000)   # 启动时一次

while True:
    img = sensor.snapshot()
    wifi_snap.poll()                     # 每帧调用，非阻塞
    if wifi_snap.is_connected():
        wifi_snap.send_image(img)        # 需要时发一帧
```

若是 ndarray 图像（AI 管线），用：

```python
ok, buf = cv2.imencode(".jpg", arr)
wifi_snap.send_bytes(buf.tobytes())
```

## 常见问题

| 现象 | 原因与处理 |
|---|---|
| 串口一直打印“正在连接 WiFi ...” | 热点不是 2.4GHz、密码错误、或加密方式是 WPA3 |
| 电脑 ping 不通 K230 | 手机热点开启了“客户端隔离/AP 隔离”，关掉它 |
| 电脑报“目标计算机积极拒绝” | K230 程序没在运行，或端口与电脑端不一致 |
| 电脑 `ipconfig` 网段异常 | 电脑还连着校园网/其他 WiFi，断开后重连热点 |
| 换热点或重启后连不上 | K230 的 IP 变了，按串口打印的新 IP 改 `K230_IP` |

## 已知问题 / 待改进

### 1. 图片文件名会覆盖（待改进）

电脑端每次启动 `index` 都从 0 开始，所以**下一次运行的第一张图会覆盖上一次的 `snapshot_001.jpg`**。

建议改法：用当前时间命名，例如 `snapshot_20261017_205315.jpg`，既不重复也便于按时间查找。

### 2. 图片分辨率偏低（待评估）

K230 端目前是 `WIDTH = 640`、`HEIGHT = 480`，单帧约 10–20 KB，传输快但细节一般。

可选提升方案：

- 分辨率提到 1280 × 720，画面更清晰，单帧体积和传输耗时相应增加
- 保持分辨率不变，只提高 JPEG 编码质量（需固件支持质量参数）

根据实际使用场景再决定是否调整。
