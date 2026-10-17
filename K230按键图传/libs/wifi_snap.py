# wifi_snap.py —— K230 WiFi 单帧图传服务端模块
#
# 职责：联网 + TCP 监听 + 发一帧 JPEG。不碰摄像头/显示屏/媒体管线。
#
# 部署：把本文件放到板子 /sdcard/libs/ 下
#
# 用法（在任意主程序里）：
#   import sys
#   sys.path.append("/sdcard/libs")
#   import wifi_snap
#
#   ip = wifi_snap.init("热点名", "密码", 8000)   # 启动时调用一次
#
#   while True:
#       img = sensor.snapshot()
#       wifi_snap.poll()                          # 每帧调用，非阻塞
#       if 需要发图:
#           wifi_snap.send_image(img)             # 编码 JPEG 并发送
#
# 协议：[4 字节大端长度][JPEG 数据]

import os
import time
import socket
import network

try:
    import select          # 用于非阻塞探测连接状态
except Exception:
    select = None          # 固件不带 select 时退化为"只在发送失败时发现断开"

# ---------------- 模块状态（MicroPython 下用全局变量最省内存） ----------------

_srv = None                     # 监听 socket，全程不关闭
_conn = None                    # 当前电脑连接
_sta = None                     # WLAN 对象，保持引用防止被回收
_ip = None                      # 本机 IP
_port = 8000
_tmp_path = "/sdcard/wifi_snap_tmp.jpg"
_poll_count = 0


# ---------------- 对外接口 ----------------


def init(ssid, password, port=8000, tmp_path="/sdcard/wifi_snap_tmp.jpg", timeout=20):
    """连接 WiFi 并开始监听，返回本机 IP；失败返回 None。

    启动时调用一次即可，重复调用会直接返回已有 IP。
    """
    global _srv, _ip, _port, _tmp_path

    if _srv is not None:
        return _ip

    _port = port
    _tmp_path = tmp_path

    ip = _connect_sta(ssid, password, timeout)
    if ip is None:
        return None

    _ip = ip
    _srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _srv.bind((ip, port))
    _srv.listen(1)
    # 短超时：即使没有 select，accept 也不会卡住主循环
    _srv.settimeout(0.01)

    print("[SNAP] 已监听 %s:%d，等待电脑连接 ..." % (ip, port))
    return ip


def poll():
    """每帧调用一次。非阻塞，返回当前是否有电脑连接。"""
    global _poll_count

    if _conn is None:
        _try_accept()
    else:
        _poll_count += 1
        # 每 30 次调用（约 30 帧）检查一次对端是否断开
        if _poll_count % 30 == 0 and not _peer_alive(_conn):
            print("[SNAP] 电脑端已断开，等待重新连接 ...")
            _close_conn()

    return _conn is not None


def is_connected():
    """当前是否有电脑连接。"""
    return _conn is not None


def local_ip():
    """返回本机 IP（init 成功后有效），用于电脑端填写。"""
    return _ip


def send_image(img):
    """把 image 对象编码成 JPEG 并发送，返回 True/False。

    img 必须支持 save(path)（media.sensor.snapshot() 的返回值即可）。
    注意：snapshot 的图是共享缓冲，调用本函数时不要先跨帧保存引用。
    """
    if _conn is None:
        return False

    try:
        img.save(_tmp_path)
    except Exception as e:
        print("[SNAP] JPEG 编码失败:", e)
        return False

    return send_file(_tmp_path)


def send_file(path):
    """按 [4字节大端长度][JPEG数据] 发送一个图片文件。"""
    if _conn is None:
        return False

    try:
        size = os.stat(path)[6]          # [6] 为文件大小
    except OSError as e:
        print("[SNAP] 读取文件失败:", e)
        return False

    if size <= 0:
        print("[SNAP] 图片为空，跳过")
        return False

    try:
        _send_all(_conn, size.to_bytes(4, "big"))

        # 分块读取发送，避免一次性把整张图读进内存
        with open(path, "rb") as f:
            remain = size
            while remain > 0:
                chunk = f.read(min(4096, remain))
                if not chunk:
                    raise OSError("文件读取提前结束")
                _send_all(_conn, chunk)
                remain -= len(chunk)
    except OSError as e:
        # 发送失败通常对端已断开，关掉连接等它重连
        print("[SNAP] 发送失败:", e, "，等待电脑重连 ...")
        _close_conn()
        return False

    print("[SNAP] 已发送", size, "字节")
    return True


def send_bytes(data):
    """发送一段已编码好的 JPEG 字节。

    适合图像是 ndarray 的场景（例如 cv2.imencode(".jpg", arr)[1].tobytes()）。
    """
    if _conn is None or not data:
        return False

    try:
        _send_all(_conn, len(data).to_bytes(4, "big"))
        _send_all(_conn, data)
    except OSError as e:
        print("[SNAP] 发送失败:", e, "，等待电脑重连 ...")
        _close_conn()
        return False

    print("[SNAP] 已发送", len(data), "字节")
    return True


def deinit():
    """关闭网络资源。不涉及摄像头/显示屏。"""
    global _srv, _ip

    _close_conn()

    if _srv is not None:
        try:
            _srv.close()
        except Exception:
            pass
        _srv = None

    _ip = None
    print("[SNAP] 网络资源已释放")


# ---------------- 内部实现 ----------------


def _connect_sta(ssid, password, timeout):
    """连接热点，返回本机 IP；失败返回 None。

    注意：本固件（rt_smart）不支持 sta.active(True)，调用会报
    "network(rt_smart) not support set active state"，所以这里不调用它。
    """
    global _sta

    _sta = network.WLAN(network.STA_IF)

    if _sta.isconnected():
        ip = _sta.ifconfig()[0]
        print("[SNAP] 已连接，本机 IP:", ip)
        return ip

    _sta.connect(ssid, password)
    for _ in range(timeout):
        if _sta.isconnected():
            break
        print("[SNAP] 正在连接 WiFi ...")
        time.sleep(1)

    if not _sta.isconnected():
        print("[SNAP] WiFi 连接失败，请检查名称/密码/信号")
        return None

    ip = _sta.ifconfig()[0]
    print("[SNAP] 连接成功，本机 IP:", ip)
    return ip


def _try_accept():
    """非阻塞地尝试接入一个电脑连接。"""
    global _conn

    if _srv is None:
        return

    # 先用 select 确认真的有连接待接入，避免 accept 白等
    if select is not None:
        try:
            readable, _, _ = select.select([_srv], [], [], 0)
            if not readable:
                return
        except Exception:
            pass          # select 不支持就算了，下面靠 accept 的短超时兜底

    try:
        conn, addr = _srv.accept()
    except OSError:
        return

    conn.settimeout(None)
    try:
        conn.setsockopt(6, 1, 1)      # IPPROTO_TCP=6, TCP_NODELAY=1
    except Exception:
        pass

    _conn = conn
    print("[SNAP] 电脑已接入:", addr[0], addr[1])


def _peer_alive(conn):
    """探测电脑端是否还连着，不向连接写入任何数据。

    不能用"recv 加短超时"来判断：本固件超时后返回空字节串 b""，
    而 b"" 在 TCP 里表示对端关闭，会把正常连接误判成断开。

    改用 select 只查询是否可读：
      - 不可读  => 电脑只收不发，说明连接正常
      - 可读    => 再 recv 一次，空字节串才表示对端真的关闭
    """
    if select is None:
        return True

    try:
        readable, _, _ = select.select([conn], [], [], 0)
    except Exception:
        return True

    if not readable:
        return True

    try:
        data = conn.recv(16)
    except Exception:
        return False

    return len(data) > 0


def _send_all(sock, data):
    """把 data 全部发完。

    sock.send() 只保证发出去一部分并返回实际字节数，
    几十 KB 的 JPEG 一次通常发不完，剩下的必须循环补发。
    """
    total = len(data)
    sent = 0
    while sent < total:
        n = sock.send(data[sent:])
        if n is None or n <= 0:
            raise OSError("send 返回 0，连接可能已断开")
        sent += n
    return sent


def _close_conn():
    """关闭当前电脑连接，回到等待接入状态。"""
    global _conn

    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None
