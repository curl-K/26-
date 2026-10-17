# 按键单帧快照 -> 通过 wifi_snap 模块发到电脑
# 本文件只演示"怎么用模块"，网络逻辑全在 /sdcard/libs/wifi_snap.py 里

import os
import sys
import time
import gc

from media.sensor import *
from media.display import *
from media.media import *
import ybUtils.YbKey as YbKey

# 模块放在板子 /sdcard/libs/ 下，需把该目录加入 import 路径
sys.path.append("/sdcard/libs")
import wifi_snap

# ============================ 需要你填写的配置 ============================

WIFI_SSID = "REDMI K80 Pro"
WIFI_PASSWORD = "123456789"

PC_PORT = 8000             # 电脑端要连这个端口
WIDTH = 640
HEIGHT = 480

# ============================ 主程序 ============================


if __name__ == "__main__":
    sensor = None
    key = YbKey.YbKey()

    try:
        # 1. 联网 + 开始监听（只做一次）
        local_ip = wifi_snap.init(WIFI_SSID, WIFI_PASSWORD, PC_PORT)
        if local_ip is None:
            raise Exception("网络未连接，程序退出")

        # 2. 初始化摄像头
        sensor = Sensor()
        sensor.reset()
        sensor.set_framesize(width=WIDTH, height=HEIGHT)
        sensor.set_pixformat(Sensor.RGB565)

        Display.init(Display.ST7701, width=WIDTH, height=HEIGHT, to_ide=True)

        MediaManager.init()
        sensor.run()

        last_pressed = False   # 上一轮按键状态，用于边沿检测
        shot_index = 0

        while True:
            os.exitpoint()

            # 取一帧原始画面，不做任何绘制（保证是纯净原始帧）
            img = sensor.snapshot()
            Display.show_image(img)

            # 每帧调用一次：没有电脑连时只做一次非阻塞检查，不卡画面
            wifi_snap.poll()

            # 只在"刚才没按、现在按了"时触发，按住不放只发一次
            pressed = key.is_pressed()
            if pressed and not last_pressed:
                shot_index += 1
                print("========== 第", shot_index, "张 ==========")

                if not wifi_snap.is_connected():
                    print("[SEND] 还没有电脑连接，本张未发送")
                elif wifi_snap.send_image(img):
                    print("[SEND] 第", shot_index, "张发送完成")

                gc.collect()

            last_pressed = pressed
            time.sleep_ms(1)

    except KeyboardInterrupt:
        print("用户停止程序")
    except BaseException as e:
        print("发生异常:", e)
    finally:
        # 3. 清理资源（与初始化顺序相反）
        wifi_snap.deinit()

        if isinstance(sensor, Sensor):
            sensor.stop()

        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()
        print("资源已释放")
