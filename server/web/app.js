const loginPanel = document.querySelector("#login");
const desk = document.querySelector("#desk");
const loginError = document.querySelector("#login-error");
const note = document.querySelector("#note");
let role = "";
let timer = 0;

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (response.status === 401) {
    showLogin();
    throw new Error(body.message || "请先登录");
  }
  return { response, body };
}

function showLogin() {
  window.clearInterval(timer);
  loginPanel.hidden = false;
  desk.hidden = true;
  role = "";
}

function showNote(message, isError) {
  note.hidden = !message;
  note.textContent = message || "";
  note.className = isError ? "note error" : "note";
}

function slotName(slot) {
  return slot === 1 ? "第一格" : "第二格";
}

function when(value) {
  return value ? value.replace("T", " ") : "";
}

function renderList(items) {
  const body = document.querySelector("#rows");
  body.replaceChildren();
  document.querySelector("#empty").hidden = items.length > 0;
  for (const item of items) {
    const row = document.createElement("tr");
    const level = document.createElement("td");
    level.textContent = item.level;
    if (item.level === "高") level.className = "high";
    row.append(
      cell(item.name),
      level,
      cell(slotName(item.slot)),
      cell(item.status),
      cell((item.handlers || []).join("、")),
      cell(when(item.at))
    );
    body.append(row);
  }
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text || "";
  return td;
}

function renderAlarms(items) {
  const list = document.querySelector("#alarm-list");
  list.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("li");
    empty.textContent = "没有告警";
    list.append(empty);
    return;
  }
  for (const alarm of items) {
    const li = document.createElement("li");
    if (alarm.acknowledged) li.className = "acked";
    const text = document.createElement("span");
    const where = alarm.slot ? slotName(alarm.slot) : "";
    text.textContent = [alarm.type, where, alarm.message, when(alarm.at)].filter(Boolean).join(" · ");
    li.append(text);
    if (!alarm.acknowledged) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "确认";
      button.addEventListener("click", () => acknowledge(alarm.id));
      li.append(button);
    }
    list.append(li);
  }
}

function renderEnv(data) {
  const online = document.querySelector("#online");
  online.textContent = data.online ? "柜旁在线" : "柜旁离线";
  online.className = data.online ? "up" : "down";
  const readings = document.querySelector("#env-readings");
  readings.replaceChildren();
  const latest = data.latest;
  if (!latest) {
    readings.append(term("读数"), desc("还没有采样"));
    return;
  }
  readings.append(
    term("温度"), desc(number(latest.temperature, "℃", "15–30", latest.tempOver)),
    term("湿度"), desc(number(latest.humidity, "%RH", "20–70", latest.humidityOver)),
    term("TVOC"), desc(number(latest.tvoc, "ppb", "≤1000", latest.tvocOver)),
    term("eCO2"), desc(number(latest.eco2, "", "≤1500", latest.eco2Over)),
    term("时间"), desc(document.createTextNode(when(latest.at)))
  );
}

function term(text) {
  const node = document.createElement("dt");
  node.textContent = text;
  return node;
}

function desc(child) {
  const node = document.createElement("dd");
  node.append(child);
  return node;
}

function number(value, unit, range, over) {
  const span = document.createElement("span");
  span.textContent = value == null ? "—" : `${value}${unit}（${range}）`;
  if (over) span.className = "over";
  return span;
}

async function refresh() {
  const list = await api("/api/reagents", { method: "GET" });
  renderList(list.body.items || []);
  if (role !== "manager") return;
  const alarms = await api("/api/alarms", { method: "GET" });
  renderAlarms(alarms.body.items || []);
  const env = await api("/api/environment", { method: "GET" });
  renderEnv(env.body);
}

async function acknowledge(id) {
  const result = await api(`/api/alarms/${id}/ack`, { method: "POST", body: "{}" });
  showNote(result.body.message, result.body.result !== "ok");
  await refresh();
}

function enter(me) {
  role = me.role;
  loginPanel.hidden = true;
  desk.hidden = false;
  document.querySelector("#who").textContent = `${me.name} · ${me.role === "manager" ? "管理人" : "取用人"}`;
  const manager = me.role === "manager";
  document.querySelector("#register").hidden = !manager;
  document.querySelector("#alarms").hidden = !manager;
  document.querySelector("#env").hidden = !manager;
  refresh().catch(() => {});
  window.clearInterval(timer);
  timer = window.setInterval(() => refresh().catch(() => {}), 2000);
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  loginError.hidden = true;
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") })
    });
    if (!result.response.ok) {
      loginError.hidden = false;
      loginError.textContent = result.body.message || "登录失败";
      return;
    }
    enter(result.body);
  } catch (error) {
    loginError.hidden = false;
    loginError.textContent = error.message;
  }
});

document.querySelector("#logout").addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST", body: "{}" }).catch(() => {});
  showLogin();
});

document.querySelector("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const result = await api("/api/reagents", {
    method: "POST",
    body: JSON.stringify({
      name: form.get("name"),
      level: form.get("level"),
      slot: Number(form.get("slot"))
    })
  });
  showNote(result.body.message, result.body.result !== "ok");
  if (result.body.result === "ok") event.target.reset();
  await refresh();
});

api("/api/auth/me", { method: "GET" }).then((result) => {
  if (result.response.ok) enter(result.body);
}).catch(() => {});
