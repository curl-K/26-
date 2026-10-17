# 电脑端：主动连接 K230，接收 JPEG 帧并保存
# 用法：python pc_recv_snapshot.py
# 协议：[4 字节大端长度][JPEG 数据]
#
# 为什么由电脑主动连接：K230 这版固件在 AP 模式下主动 connect() 会报
# ECONNABORTED，所以改成 K230 监听、电脑连接。

import os
import socket
import struct
import time

K230_IP = "10.236.192.250"   # K230 串口打印的 IP（STA 模式由手机热点分配，每次可能不同）
K230_PORT = 8000
# 保存目录固定到脚本所在目录，避免从别处启动时图片存到意外位置
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received")


def recv_exact(conn, n):
    """必须收满 n 字节才返回。

    TCP 的 recv 可能一次只收到几个字节，不循环收就无法正确切帧。
    """
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None          # 对端断开
        buf += chunk
    return buf


def connect_k230():
    """反复尝试连接 K230，直到成功"""
    while True:
        try:
            conn = socket.create_connection((K230_IP, K230_PORT), timeout=3)
            print(f"已连接 K230: {K230_IP}:{K230_PORT}")
            conn.settimeout(None)
            return conn
        except OSError as e:
            print(f"连接 K230 失败({e})，2 秒后重试 ...")
            time.sleep(2)


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    print(f"图片保存目录: {os.path.abspath(SAVE_DIR)}")
    print(f"目标 K230: {K230_IP}:{K230_PORT}")
    print("请确认电脑和 K230 都连在同一个手机热点上，且 K230 端脚本已运行")

    index = 0
    while True:
        conn = connect_k230()
        try:
            while True:
                hdr = recv_exact(conn, 4)
                if hdr is None:
                    print("K230 断开连接，准备重连 ...")
                    break

                size = struct.unpack(">I", hdr)[0]
                if size <= 0 or size > 20 * 1024 * 1024:
                    print(f"长度异常({size})，协议错位，准备重连 ...")
                    break

                t0 = time.time()
                data = recv_exact(conn, size)
                if data is None:
                    print("数据未收完，连接断开，准备重连 ...")
                    break
                cost = (time.time() - t0) * 1000

                index += 1
                path = os.path.join(SAVE_DIR, f"snapshot_{index:03d}.jpg")
                with open(path, "wb") as f:
                    f.write(data)

                print(f"[{index}] 收到 {size} 字节，耗时 {cost:.1f} ms -> {path}")

        except KeyboardInterrupt:
            print("用户停止")
            return
        finally:
            conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("用户停止")
