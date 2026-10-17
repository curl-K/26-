# K230 WiFi 扫描测试：确认能否扫到目标 WiFi，以及频段
# 用法：CanMV IDE 打开本文件直接运行，看串口终端输出

import network

sta = network.WLAN(network.STA_IF)
if not sta.active():
    sta.active(True)

print("开始扫描 WiFi ...")
aps = sta.scan()

if not aps:
    print("没有扫描到任何 WiFi，请检查模块天线/供电")
else:
    # 按信号强度从强到弱排序，方便看清
    aps.sort(key=lambda a: a.RSSI, reverse=True)
    print("共扫描到", len(aps), "个信号：")
    print("SSID                         信道  信号   频段")
    for ap in aps:
        try:
            ssid = ap.ssid
        except Exception:
            ssid = "?"
        ch = ap.channel
        band = "2.4G" if ch <= 14 else "5G"
        print("%-28s %-5d %-6d %s" % (ssid, ch, ap.RSSI, band))

print("\n如果上面没有出现 whpu-student，说明 K230 扫不到这个 5G 信号，")
print("请改用 AP 模式（K230 开热点，电脑连 K230）。")
