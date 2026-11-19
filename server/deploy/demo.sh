#!/bin/bash
# 在树莓派上走通报告第 6.1 节里服务器能独立完成的步骤。数据库应是刚装好的空清单。
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  exec sudo bash "$0" "$@"
fi
set -a
# shellcheck disable=SC1091
. /etc/reagent-server.env
set +a

BASE=http://127.0.0.1/api
SEQ=0
CJ=/tmp/reagent-demo-cookies
rm -f "$CJ"

if ! curl -sf "$BASE/actuator/health" >/dev/null; then
  echo "清单服务没在 80 端口应答。先看 systemctl status reagent-server nginx"
  exit 1
fi

next() {
  SEQ=$((SEQ + 1))
  echo "$SEQ"
}

result_of() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("result",""))'
}

expect() {
  local got
  got=$(result_of "$2")
  if [ "$got" != "$1" ]; then
    echo "期望 $1"
    echo "实际 $2"
    exit 1
  fi
  echo "OK $1"
}

web() {
  curl -s -b "$CJ" -H 'Content-Type: application/json' "$@"
}

device() {
  local path="$1"
  local json="$2"
  curl -s -H "X-Device-Token: ${DEVICE_TOKEN}" -H 'Content-Type: application/json' -d "$json" "$BASE$path"
}

login=$(curl -s -c "$CJ" -H 'Content-Type: application/json' \
  -d '{"username":"manager","password":"manager123"}' "$BASE/auth/login")
python3 -c 'import json,sys; body=json.loads(sys.argv[1]); assert body.get("role")=="manager", body' "$login"
echo "OK 管理人登录"

bad=$(device /device/confirm "{\"seq\":$(next),\"slot\":1,\"username\":\"chen\",\"password\":\"nope\"}")
expect bad_password "$bad"

first=$(web -d '{"name":"乙醇","level":"低","slot":1}' "$BASE/reagents")
expect ok "$first"
second=$(web -d '{"name":"另一瓶","level":"中","slot":1}' "$BASE/reagents")
expect pending_exists "$second"
echo "1. 第一格只有一条待绑定"

allow=$(device /device/confirm "{\"seq\":$(next),\"slot\":1,\"username\":\"chen\",\"password\":\"chen123\"}")
expect allow "$allow"
seen=$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"E1\"}")
expect seen "$seen"
bound=$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"E1\"}")
expect recorded "$bound"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
raw = subprocess.check_output(["curl","-s","-b",cookie, base+"/reagents"], text=True)
items = json.loads(raw)["items"]
row = next(item for item in items if item["name"]=="乙醇")
assert row["status"]=="在柜" and row["handlers"]==["陈"] and row["level"]=="低" and row["slot"]==1, row
print("2. OK 清单出现乙醇，经手人陈")
PY

expect closed "$(device /device/session/end "{\"seq\":$(next),\"slot\":1,\"reason\":\"button\"}")"
expect allow "$(device /device/confirm "{\"seq\":$(next),\"slot\":1,\"username\":\"chen\",\"password\":\"chen123\"}")"
expect seen "$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"E1\"}")"
expect ignored "$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"E1\"}")"
expect seen "$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"\"}")"
expect recorded "$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"\"}")"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
raw = subprocess.check_output(["curl","-s","-b",cookie, base+"/reagents"], text=True)
row = next(item for item in json.loads(raw)["items"] if item["name"]=="乙醇")
assert row["status"]=="已取出" and row["handlers"]==["陈"] and row["at"], row
print("3. OK 已取出，经手人和时间还在")
PY

expect closed "$(device /device/session/end "{\"seq\":$(next),\"slot\":1,\"reason\":\"button\"}")"
expect ok "$(web -d '{"name":"硫酸","level":"高","slot":2}' "$BASE/reagents")"
expect need_second "$(device /device/confirm "{\"seq\":$(next),\"slot\":2,\"username\":\"chen\",\"password\":\"chen123\"}")"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
raw = subprocess.check_output(["curl","-s","-b",cookie, base+"/reagents"], text=True)
row = next(item for item in json.loads(raw)["items"] if item["name"]=="硫酸")
assert row["status"]=="待绑定" and row["handlers"]==[], row
print("4. OK 只有一人时清单不变")
PY
expect same_account "$(device /device/confirm "{\"seq\":$(next),\"slot\":2,\"username\":\"chen\",\"password\":\"chen123\"}")"
expect need_second "$(device /device/confirm "{\"seq\":$(next),\"slot\":2,\"username\":\"chen\",\"password\":\"chen123\"}")"
expect allow "$(device /device/confirm "{\"seq\":$(next),\"slot\":2,\"username\":\"li\",\"password\":\"li123\"}")"
expect seen "$(device /device/chip "{\"seq\":$(next),\"slot\":2,\"uid\":\"H1\"}")"
expect recorded "$(device /device/chip "{\"seq\":$(next),\"slot\":2,\"uid\":\"H1\"}")"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
raw = subprocess.check_output(["curl","-s","-b",cookie, base+"/reagents"], text=True)
row = next(item for item in json.loads(raw)["items"] if item["name"]=="硫酸")
assert row["status"]=="在柜" and row["handlers"]==["陈","李"], row
print("5. OK 两名经手人")
PY

expect closed "$(device /device/session/end "{\"seq\":$(next),\"slot\":2,\"reason\":\"button\"}")"
expect allow "$(device /device/confirm "{\"seq\":$(next),\"slot\":1,\"username\":\"chen\",\"password\":\"chen123\"}")"
expect seen "$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"XX\"}")"
expect unbound_chip "$(device /device/chip "{\"seq\":$(next),\"slot\":1,\"uid\":\"XX\"}")"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
rows = json.loads(subprocess.check_output(["curl","-s","-b",cookie, base+"/reagents"], text=True))["items"]
alarms = json.loads(subprocess.check_output(["curl","-s","-b",cookie, base+"/alarms"], text=True))["items"]
assert len(rows)==2, rows
assert any(item["code"]=="unbound_chip" for item in alarms), alarms
print("6. OK 未登记芯片只告警")
PY

expect ok "$(device /device/environment "{\"seq\":$(next),\"temperature\":25,\"humidity\":40,\"tvoc\":2000,\"eco2\":600}")"
expect ok "$(device /device/environment "{\"seq\":$(next),\"temperature\":25,\"humidity\":40,\"tvoc\":2000,\"eco2\":600}")"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
alarms = json.loads(subprocess.check_output(["curl","-s","-b",cookie, base+"/alarms"], text=True))["items"]
assert not any(item["code"]=="env" for item in alarms)
print("7. OK 两次越限不告警")
PY
expect ok "$(device /device/environment "{\"seq\":$(next),\"temperature\":25,\"humidity\":40,\"tvoc\":2000,\"eco2\":600}")"
python3 - "$CJ" "$BASE" <<'PY'
import json, subprocess, sys
cookie, base = sys.argv[1], sys.argv[2]
alarms = json.loads(subprocess.check_output(["curl","-s","-b",cookie, base+"/alarms"], text=True))["items"]
rows = json.loads(subprocess.check_output(["curl","-s","-b",cookie, base+"/reagents"], text=True))["items"]
assert sum(1 for item in alarms if item["code"]=="env")==1, alarms
assert len(rows)==2
print("7. OK 第三次越限才告警，清单不变")
print("服务器侧演示步骤走完。断网不开格由柜旁完成本地拒绝，未送达的事件不会出现在这份清单里。")
PY
