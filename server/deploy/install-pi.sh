#!/bin/bash
# 把整个 server 文件夹拷到树莓派后，进入该目录执行：sudo bash deploy/install-pi.sh
# 装 JDK 17、PostgreSQL、Nginx。不升级整张系统，也不进入 ROS 的 Docker。
# 这一次 apt 需要树莓派能上网。没有路由器时，可先用手机热点或电脑网线共享，装完再回到 Pi_Hot。
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "请用 sudo bash deploy/install-pi.sh"
  exit 1
fi
if [ -f /.dockerenv ]; then
  echo "请在树莓派宿主机上运行，不要进 ROS 的 Docker。"
  exit 1
fi

ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ -f "$ROOT/app.jar" ]; then
  JAR="$ROOT/app.jar"
elif [ -f "$ROOT/target/reagent-server.jar" ]; then
  JAR="$ROOT/target/reagent-server.jar"
else
  echo "没找到 app.jar。在这台电脑的 server 目录执行 .\\mvnw.cmd clean package，再把 server 文件夹拷到树莓派。"
  exit 1
fi
if [ ! -f "$ROOT/web/index.html" ]; then
  echo "没找到 web/index.html"
  exit 1
fi

JAVA_BIN=/usr/lib/jvm/java-17-openjdk-arm64/bin/java
echo "正在安装 JDK 17、PostgreSQL 和 Nginx。这一步需要树莓派能上网。"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openjdk-17-jdk-headless postgresql postgresql-contrib nginx curl
if [ ! -x "$JAVA_BIN" ]; then
  echo "没找到 $JAVA_BIN。请确认这是 64 位 Raspberry Pi OS。"
  exit 1
fi
timedatectl set-timezone Asia/Shanghai || true

if ! id appsvc >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin appsvc
fi

systemctl enable --now postgresql
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then
    break
  fi
  sleep 1
done

if [ -f /etc/reagent-server.env ]; then
  set -a
  # shellcheck disable=SC1091
  . /etc/reagent-server.env
  set +a
else
  DB_PASSWORD=$(openssl rand -hex 16)
  DEVICE_TOKEN=$(openssl rand -hex 24)
  printf 'DB_PASSWORD=%s\nDEVICE_TOKEN=%s\n' "$DB_PASSWORD" "$DEVICE_TOKEN" > /etc/reagent-server.env
fi
chown root:appsvc /etc/reagent-server.env
chmod 640 /etc/reagent-server.env

if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='reagent'" | grep -q 1; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER USER reagent WITH PASSWORD '${DB_PASSWORD}'"
else
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE USER reagent WITH PASSWORD '${DB_PASSWORD}'"
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='reagent_db'" | grep -q 1; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE reagent_db OWNER reagent"
fi

install -d -o appsvc -g appsvc /opt/reagent-server
install -o appsvc -g appsvc -m 644 "$JAR" /opt/reagent-server/app.jar
install -o appsvc -g appsvc -m 750 "$ROOT/deploy/start.sh" /opt/reagent-server/start.sh
install -d -o www-data -g www-data /var/www/reagent
rm -rf /var/www/reagent/*
cp -a "$ROOT/web/." /var/www/reagent/
chown -R www-data:www-data /var/www/reagent

install -m 644 "$ROOT/deploy/nginx-reagent.conf" /etc/nginx/sites-available/reagent
ln -sfn /etc/nginx/sites-available/reagent /etc/nginx/sites-enabled/reagent
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

install -m 644 "$ROOT/deploy/reagent-server.service" /etc/systemd/system/reagent-server.service
systemctl daemon-reload
systemctl enable reagent-server
systemctl restart reagent-server

ready=0
for _ in $(seq 1 20); do
  if curl -sf http://127.0.0.1:8080/api/actuator/health >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "服务没有在 8080 上起来。执行 journalctl -u reagent-server -n 80 --no-pager"
  exit 1
fi

echo
echo "清单页面（电脑先连到和树莓派同一个网络，热点名 Pi_Hot，密码 12345678）："
hostname -I | tr ' ' '\n' | while read -r ip; do
  if [ -n "$ip" ]; then
    echo "  http://${ip}/"
  fi
done
echo "演示账号：管理人 manager / manager123，取用人 chen / chen123，li / li123"
echo "柜旁设备令牌在 /etc/reagent-server.env 的 DEVICE_TOKEN"
echo "验收：sudo bash deploy/demo.sh"
