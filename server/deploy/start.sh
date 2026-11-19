#!/bin/sh
MEM_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
XMX=512m
if [ "${MEM_KB:-0}" -lt 3500000 ]; then
  XMX=384m
fi
exec /usr/lib/jvm/java-17-openjdk-arm64/bin/java -Xms128m -Xmx"$XMX" -XX:+UseSerialGC \
  -jar /opt/reagent-server/app.jar --spring.profiles.active=prod
