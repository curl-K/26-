const loginPanel = document.querySelector("#login");
const desk = document.querySelector("#desk");
const loginError = document.querySelector("#login-error");
const note = document.querySelector("#note");

let role = "";
let view = "desk";
let timer = 0;
let items = [];
let alarms = [];
let env = null;
let people = [];
let personFocus = null;
let personDetailKey = "";
const LAST_MANAGER_REASON = "须至少保留一名管理人";
const PERSON_ACTIONS = [
  ["查看", "view"],
  ["改角色", "role"],
  ["停用或启用", "status"],
  ["修改密码", "password"],
  ["重置密码", "reset"]
];
const envCharts = {};
const ENV_SERIES = [
  { key: "temperature", label: "温度", unit: "℃", color: "#0f766e", overFlag: "tempOver", lines: [{ y: 15, text: "15℃" }, { y: 30, text: "30℃" }] },
  { key: "humidity", label: "湿度", unit: "%RH", color: "#1d4ed8", overFlag: "humidityOver", lines: [{ y: 20, text: "20%RH" }, { y: 70, text: "70%RH" }] },
  { key: "tvoc", label: "TVOC", unit: "ppb", color: "#b45309", overFlag: "tvocOver", lines: [{ y: 1000, text: "1000 ppb" }] },
  { key: "eco2", label: "eCO2", unit: "", color: "#64748b", overFlag: "eco2Over", lines: [{ y: 1500, text: "1500" }] }
];
const filters = { q: "", level: "全部", status: "全部" };

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
  applyRemembered();
}

const REMEMBER_KEY = "reagent-remember";

function readRemembered() {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function applyRemembered() {
  const saved = readRemembered();
  const form = document.querySelector("#login-form");
  const password = form.querySelector("[name=password]");
  const toggle = form.querySelector(".secret-toggle");
  form.querySelector("[name=remember]").checked = Boolean(saved);
  form.querySelector("[name=username]").value = saved ? saved.username || "" : "";
  password.value = saved ? saved.password || "" : "";
  password.type = "password";
  if (toggle) toggle.textContent = "显示";
}

function storeRemembered(username, password, remember) {
  if (remember) localStorage.setItem(REMEMBER_KEY, JSON.stringify({ username, password }));
  else localStorage.removeItem(REMEMBER_KEY);
}

function showNote(message, isError) {
  note.hidden = !message;
  note.textContent = message || "";
  note.className = isError ? "toast is-error" : "toast";
}

function slotName(slot) {
  return slot === 1 ? "第一格" : "第二格";
}

function when(value) {
  return value ? value.replace("T", " ") : "";
}

function badge(text, kind) {
  const span = document.createElement("span");
  span.className = "badge" + (kind ? " " + kind : "");
  span.textContent = text;
  return span;
}

function levelBadge(level) {
  return badge(level, level === "高" ? "level-high" : "");
}

function statusBadge(status) {
  const kind = status === "在柜" ? "status-in" : status === "已取出" ? "status-out" : "status-pending";
  return badge(status, kind);
}

function cell(node, className) {
  const td = document.createElement("td");
  if (className) td.className = className;
  if (typeof node === "string") td.textContent = node;
  else td.append(node);
  return td;
}

function filteredItems() {
  return items.filter((item) => {
    const nameOk = !filters.q || item.name.includes(filters.q);
    const levelOk = filters.level === "全部" || item.level === filters.level;
    const statusOk = filters.status === "全部" || item.status === filters.status;
    return nameOk && levelOk && statusOk;
  });
}

function fillTable(id, rows, emptyId, allowDelete) {
  const body = document.querySelector("#" + id);
  body.replaceChildren();
  document.querySelector("#" + emptyId).hidden = rows.length > 0;
  for (const item of rows) {
    const row = document.createElement("tr");
    if (allowDelete) {
      row.append(
        cell(item.name, "col-name"),
        cell(levelBadge(item.level), "col-level"),
        cell(slotName(item.slot), "col-slot"),
        cell(statusBadge(item.status), "col-status"),
        cell((item.handlers || []).join("、") || "—", "col-handler"),
        cell(when(item.at) || "—", "col-time")
      );
    } else {
      row.append(
        cell(item.name),
        cell(levelBadge(item.level)),
        cell(slotName(item.slot)),
        cell(statusBadge(item.status)),
        cell((item.handlers || []).join("、")),
        cell(when(item.at))
      );
    }
    if (allowDelete && role === "manager") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ghost";
      button.textContent = "删除";
      button.addEventListener("click", () => removeReagent(item));
      row.append(cell(button, "col-action"));
    }
    body.append(row);
  }
}

function renderStats() {
  const inCabinet = items.filter((item) => item.status === "在柜").length;
  const taken = items.filter((item) => item.status === "已取出").length;
  const high = items.filter((item) => item.level === "高").length;
  const pending = items.filter((item) => item.status === "待绑定").length;
  const openAlarms = alarms.filter((alarm) => !alarm.acknowledged).length;
  const cards = [
    ["在柜", inCabinet],
    ["已取出", taken],
    ["高等级试剂", high],
    role === "manager" ? ["未处理告警", openAlarms] : ["待绑定", pending]
  ];
  const box = document.querySelector("#stats");
  box.replaceChildren();
  for (const [label, value] of cards) {
    const card = document.createElement("article");
    card.className = "stat";
    const span = document.createElement("span");
    span.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = String(value);
    card.append(span, strong);
    box.append(card);
  }
}

function occupying(slot) {
  return items.filter((item) => item.slot === slot && (item.status === "在柜" || item.status === "待绑定"));
}

function renderSlots() {
  const box = document.querySelector("#slots");
  box.replaceChildren();
  for (const slot of [1, 2]) {
    const bottles = occupying(slot);
    const card = document.createElement("article");
    const high = bottles.some((item) => item.level === "高");
    card.className = "slot" + (bottles.length ? "" : " empty") + (high ? " high" : "");
    const title = document.createElement("p");
    title.className = "slot-title";
    title.textContent = slotName(slot);
    const body = document.createElement("div");
    body.className = "slot-body";
    if (!bottles.length) {
      body.textContent = "空";
    } else {
      for (const item of bottles) {
        const line = document.createElement("div");
        line.className = "bottle";
        const name = document.createElement("strong");
        name.textContent = item.name;
        line.append(name, levelBadge(item.level), statusBadge(item.status));
        body.append(line);
      }
    }
    card.append(title, body);
    box.append(card);
  }
}

function renderAlarms() {
  const list = document.querySelector("#alarm-list");
  const count = document.querySelector("#alarm-count");
  list.replaceChildren();
  const open = alarms.filter((alarm) => !alarm.acknowledged).length;
  count.textContent = "未确认 " + open;
  if (!alarms.length) {
    const empty = document.createElement("article");
    empty.className = "alarm-card";
    const body = document.createElement("div");
    body.className = "alarm-body";
    const title = document.createElement("h3");
    title.textContent = "没有告警";
    body.append(title);
    empty.append(body);
    list.append(empty);
    return;
  }
  const ordered = [...alarms].sort((a, b) => Number(a.acknowledged) - Number(b.acknowledged));
  for (const alarm of ordered) {
    const card = document.createElement("article");
    card.className = "alarm-card" + (alarm.code === "env" ? " env" : "") + (alarm.acknowledged ? " acked" : "");
    const body = document.createElement("div");
    body.className = "alarm-body";
    const title = document.createElement("h3");
    title.textContent = alarm.type || "告警";
    const detail = document.createElement("p");
    detail.className = "muted";
    const where = alarm.slot ? slotName(alarm.slot) : "";
    detail.textContent = [where, alarm.message].filter(Boolean).join(" · ");
    const time = document.createElement("time");
    time.textContent = when(alarm.at);
    body.append(title, detail, time);
    card.append(body);
    if (!alarm.acknowledged && role === "manager") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ghost";
      button.textContent = "确认";
      button.addEventListener("click", () => acknowledge(alarm.id));
      card.append(button);
    }
    list.append(card);
  }
}

function renderEnv() {
  const online = document.querySelector("#online");
  const readings = document.querySelector("#env-readings");
  const time = document.querySelector("#env-time");
  readings.replaceChildren();
  if (!env) {
    destroyEnvCharts();
    online.textContent = "柜旁离线";
    online.className = "badge down";
    time.textContent = "";
    return;
  }
  online.textContent = env.online ? "柜旁在线" : "柜旁离线";
  online.className = env.online ? "badge up" : "badge down";
  const latest = env.latest;
  if (!latest) {
    time.textContent = "还没有采样";
  } else {
    const cards = [
      ["温度", latest.temperature, "℃", "15–30", latest.tempOver],
      ["湿度", latest.humidity, "%RH", "20–70", latest.humidityOver],
      ["TVOC", latest.tvoc, "ppb", "≤1000", latest.tvocOver],
      ["eCO2", latest.eco2, "", "≤1500", latest.eco2Over]
    ];
    for (const [label, value, unit, range, over] of cards) {
      const card = document.createElement("article");
      card.className = over ? "reading over" : "reading";
      const span = document.createElement("span");
      span.textContent = label + " " + range;
      const strong = document.createElement("strong");
      strong.textContent = value == null ? "—" : `${value}${unit}`;
      card.append(span, strong);
      readings.append(card);
    }
    time.textContent = "采样时间 " + when(latest.at);
  }
  ensureEnvCharts();
  for (const spec of ENV_SERIES) syncEnvChart(spec);
}

function ensureEnvCharts() {
  const charts = document.querySelector("#env-charts");
  if (charts.dataset.ready === "1") return;
  charts.replaceChildren();
  for (const spec of ENV_SERIES) {
    const card = document.createElement("article");
    card.className = "card chart-card";
    const title = document.createElement("h2");
    title.textContent = spec.label;
    const host = document.createElement("div");
    host.id = "chart-" + spec.key;
    host.className = "chart-host";
    const empty = document.createElement("p");
    empty.className = "muted chart-empty";
    empty.hidden = true;
    empty.textContent = "还没有足够的采样";
    card.append(title, host, empty);
    charts.append(card);
  }
  charts.dataset.ready = "1";
}

function destroyEnvCharts() {
  for (const key of Object.keys(envCharts)) {
    envCharts[key].destroy();
    delete envCharts[key];
  }
  const charts = document.querySelector("#env-charts");
  charts.replaceChildren();
  delete charts.dataset.ready;
}

function envChartOptions(spec, seq, color) {
  const marks = spec.lines.map((line) => line.y);
  const values = seq.map((point) => point[spec.key]);
  let min = Math.min(...values, ...marks);
  let max = Math.max(...values, ...marks);
  const pad = (max - min) * 0.08 || 1;
  min -= pad;
  max += pad;
  return {
    chart: {
      type: "area",
      height: 220,
      toolbar: { show: false },
      fontFamily: "Source Han Sans SC, Noto Sans SC, Microsoft YaHei, sans-serif",
      animations: { enabled: true, speed: 400, dynamicAnimation: { enabled: false } },
      zoom: { enabled: false }
    },
    series: [{
      name: spec.label,
      data: seq.map((point) => [new Date(point.at).getTime(), point[spec.key]])
    }],
    stroke: { curve: "smooth", width: 2, colors: [color] },
    colors: [color],
    fill: {
      type: "gradient",
      gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.02, stops: [0, 100] }
    },
    dataLabels: { enabled: false },
    grid: { borderColor: "#e4e4e7" },
    xaxis: {
      type: "datetime",
      labels: { datetimeUTC: false, style: { colors: "#71717a", fontSize: "11px" } },
      axisBorder: { color: "#e4e4e7" },
      axisTicks: { color: "#e4e4e7" }
    },
    yaxis: {
      min,
      max,
      labels: { style: { colors: "#71717a", fontSize: "11px" } },
      decimalsInFloat: spec.key === "tvoc" || spec.key === "eco2" ? 0 : 1
    },
    markers: { size: 0, hover: { size: 5 } },
    tooltip: {
      intersect: false,
      shared: false,
      followCursor: true,
      x: { format: "yyyy-MM-dd HH:mm:ss" },
      y: { formatter: (value) => (value == null ? "" : value + spec.unit) }
    },
    annotations: {
      yaxis: spec.lines.map((line) => ({
        y: line.y,
        borderColor: "#a1a1aa",
        strokeDashArray: 4,
        label: {
          text: line.text,
          borderColor: "#e4e4e7",
          position: "left",
          style: { color: "#3f3f46", background: "#fafafa", fontSize: "11px" }
        }
      }))
    }
  };
}

function syncEnvChart(spec) {
  const host = document.querySelector("#chart-" + spec.key);
  const empty = host.parentElement.querySelector(".chart-empty");
  const seq = (env.history || []).filter((point) => point[spec.key] != null);
  if (seq.length < 2 || typeof ApexCharts === "undefined") {
    if (envCharts[spec.key]) {
      envCharts[spec.key].destroy();
      delete envCharts[spec.key];
    }
    host.hidden = true;
    empty.hidden = false;
    return;
  }
  host.hidden = false;
  empty.hidden = true;
  const color = env.latest && env.latest[spec.overFlag] ? "#b91c1c" : spec.color;
  const options = envChartOptions(spec, seq, color);
  const chart = envCharts[spec.key];
  if (chart) {
    if (chart.__reagentColor !== color) {
      chart.updateOptions({
        colors: options.colors,
        stroke: options.stroke,
        fill: options.fill
      }, false, false);
      chart.__reagentColor = color;
    }
    chart.updateSeries(options.series, false);
    return;
  }
  const created = new ApexCharts(host, options);
  created.__reagentColor = color;
  envCharts[spec.key] = created;
  created.render();
}

function render() {
  renderStats();
  renderSlots();
  const recent = items.slice(0, 6);
  fillTable("desk-rows", recent, "desk-empty", false);
  fillTable("list-rows", filteredItems(), "list-empty", true);
  renderAlarms();
  renderEnv();
  if (role === "manager") renderPeople();
}

function renderPeople() {
  const body = document.querySelector("#people-rows");
  const empty = document.querySelector("#people-empty");
  empty.hidden = people.length > 0;
  const rows = [...body.querySelectorAll(":scope > tr[data-username]")];
  const same = rows.length === people.length && rows.every((row, index) => row.dataset.username === (people[index].username || ""));
  if (same) {
    for (const person of people) {
      const row = body.querySelector(`tr[data-username="${CSS.escape(person.username || "")}"]`);
      row.querySelector(".col-name").textContent = person.name || "";
      row.querySelector(".col-handler").textContent = person.username || "";
      row.querySelector(".col-level .badge").textContent = person.role || "";
      row.querySelector(".col-status .badge").textContent = person.status || "启用";
      lockManagerActions(row, person);
    }
    placePersonDetail();
    return;
  }
  document.querySelector("#person-detail-park").append(document.querySelector("#person-detail"));
  body.replaceChildren();
  for (const person of people) {
    const row = document.createElement("tr");
    row.dataset.username = person.username || "";
    const name = document.createElement("td");
    name.className = "col-name";
    name.textContent = person.name || "";
    const username = document.createElement("td");
    username.className = "col-handler";
    username.textContent = person.username || "";
    const roleCell = document.createElement("td");
    roleCell.className = "col-level";
    const roleBadge = document.createElement("span");
    roleBadge.className = "badge";
    roleBadge.textContent = person.role || "";
    roleCell.append(roleBadge);
    const status = document.createElement("td");
    status.className = "col-status";
    const statusBadge = document.createElement("span");
    statusBadge.className = "badge status-in";
    statusBadge.textContent = person.status || "启用";
    status.append(statusBadge);
    const action = document.createElement("td");
    action.className = "col-action";
    const actions = document.createElement("div");
    actions.className = "people-actions";
    const wide = document.createElement("div");
    wide.className = "people-wide";
    for (const [label, mode] of PERSON_ACTIONS) {
      wide.append(personAction(label, mode, () => openPerson(person, mode)));
    }
    const narrow = document.createElement("div");
    narrow.className = "menu people-narrow";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "menu-trigger";
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-label", "操作");
    const value = document.createElement("span");
    value.className = "menu-value";
    value.textContent = "操作";
    const caret = document.createElement("span");
    caret.className = "menu-caret";
    caret.setAttribute("aria-hidden", "true");
    trigger.append(value, caret);
    const panel = document.createElement("div");
    panel.className = "menu-panel";
    panel.hidden = true;
    for (const [label, mode] of PERSON_ACTIONS) {
      const option = document.createElement("button");
      option.type = "button";
      option.dataset.action = mode;
      option.textContent = label;
      panel.append(option);
    }
    narrow.append(trigger, panel);
    actions.append(wide);
    action.append(actions, narrow);
    row.append(name, username, roleCell, status, action);
    lockManagerActions(row, person);
    body.append(row);
  }
  placePersonDetail();
}

function parkPersonDetail() {
  const detail = document.querySelector("#person-detail");
  const park = document.querySelector("#person-detail-park");
  if (detail && park && detail.parentElement !== park) park.append(detail);
}

function removePersonDetailRows() {
  parkPersonDetail();
  document.querySelectorAll(".person-detail-row").forEach((row) => row.remove());
}

function placePersonDetail() {
  const body = document.querySelector("#people-rows");
  if (!personFocus) {
    removePersonDetailRows();
    return;
  }
  const current = people.find((person) => person.username === personFocus.username);
  if (!current) {
    closePerson();
    return;
  }
  const row = body.querySelector(`tr[data-username="${CSS.escape(current.username)}"]`);
  if (!row) return;
  let detailRow = row.nextElementSibling;
  if (!detailRow || !detailRow.classList.contains("person-detail-row")) {
    removePersonDetailRows();
    detailRow = document.createElement("tr");
    detailRow.className = "person-detail-row";
    const cell = document.createElement("td");
    cell.colSpan = 5;
    detailRow.append(cell);
    row.after(detailRow);
  } else {
    parkPersonDetail();
    body.querySelectorAll(".person-detail-row").forEach((item) => {
      if (item !== detailRow) item.remove();
    });
  }
  const cell = detailRow.querySelector("td");
  const detail = document.querySelector("#person-detail");
  if (detail && detail.parentElement !== cell) cell.append(detail);
  showPersonDetail(current, personFocus.mode);
}

function personAction(label, mode, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ghost";
  button.dataset.action = mode;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function isLastManager(person) {
  const managers = people.filter((item) => item.role === "管理人" && item.status !== "停用");
  return managers.length <= 1 && managers.some((item) => item.username === person.username);
}

function lockManagerActions(row, person) {
  const locked = isLastManager(person);
  row.querySelectorAll("[data-action='role'], [data-action='status']").forEach((button) => {
    button.disabled = locked;
    if (locked) button.title = LAST_MANAGER_REASON;
    else button.removeAttribute("title");
  });
  row.querySelectorAll(".lock-note").forEach((note) => note.remove());
  if (!locked) return;
  const wideNote = document.createElement("p");
  wideNote.className = "lock-note";
  wideNote.textContent = LAST_MANAGER_REASON;
  row.querySelector(".people-actions").append(wideNote);
  const menuNote = document.createElement("p");
  menuNote.className = "lock-note";
  menuNote.textContent = LAST_MANAGER_REASON;
  row.querySelector(".people-narrow .menu-panel").append(menuNote);
}

function maskPersonPassword() {
  const node = document.querySelector("#person-fact-password");
  const button = document.querySelector("#person-password-reveal");
  node.textContent = "••••••";
  node.dataset.shown = "false";
  button.textContent = "显示";
}

function fillPersonFacts(person) {
  document.querySelector("#person-name").textContent = person.name || "";
  document.querySelector("#person-username").textContent = person.username || "";
  document.querySelector("#person-fact-role").textContent = person.role || "";
  document.querySelector("#person-fact-status").textContent = person.status || "启用";
  document.querySelector("#person-role-account").textContent = person.username || "";
  document.querySelector("#person-status-account").textContent = person.username || "";
}

function setMenuValue(menu, value) {
  const hidden = menu.parentElement.querySelector(`input[name="${menu.dataset.input}"]`);
  if (hidden) hidden.value = value;
  const match = [...menu.querySelectorAll("[data-value]")].find((item) => item.dataset.value === String(value));
  const label = menu.querySelector(".menu-value");
  if (match && label) label.textContent = match.textContent;
  menu.querySelectorAll("[data-value]").forEach((item) => {
    item.classList.toggle("is-on", item.dataset.value === String(value));
  });
}

function showPersonDetail(person, mode) {
  const key = person.username + ":" + mode;
  const changed = personDetailKey !== key;
  personDetailKey = key;
  const detail = document.querySelector("#person-detail");
  detail.hidden = false;
  fillPersonFacts(person);
  const panels = { view: "#person-view", role: "#person-role", status: "#person-status", password: "#person-password", reset: "#person-reset" };
  for (const [name, selector] of Object.entries(panels)) {
    document.querySelector(selector).hidden = name !== mode;
  }
  const titles = { view: "查看", role: "改角色", status: "停用或启用", password: "修改密码", reset: "重置密码" };
  document.querySelector("#person-detail-title").textContent = titles[mode] + " · " + (person.name || person.username);
  if (!changed) return;
  maskPersonPassword();
  const passwordForm = document.querySelector("#person-password");
  passwordForm.reset();
  resetSecretToggles(passwordForm);
  const roleMenu = document.querySelector("#person-role .menu");
  if (roleMenu) setMenuValue(roleMenu, person.role || "取用人");
  const statusMenu = document.querySelector("#person-status .menu");
  if (statusMenu) setMenuValue(statusMenu, person.status || "启用");
}

function openPerson(person, mode) {
  if ((mode === "role" || mode === "status") && isLastManager(person)) {
    showNote(LAST_MANAGER_REASON, true);
    return;
  }
  if (personFocus && personFocus.username === person.username && personFocus.mode === mode) {
    closePerson();
    renderPeople();
    return;
  }
  personFocus = { username: person.username, mode };
  renderPeople();
}

function closePerson() {
  personFocus = null;
  personDetailKey = "";
  const detail = document.querySelector("#person-detail");
  if (detail) detail.hidden = true;
  removePersonDetailRows();
}

function passwordProblem(password, confirm) {
  if (!password || !confirm) return "密码不能为空";
  if (password !== confirm) return "两次密码不一致";
  return "";
}

function resetSecretToggles(root) {
  root.querySelectorAll(".secret").forEach((secret) => {
    const input = secret.querySelector("input");
    const button = secret.querySelector(".secret-toggle");
    input.type = "password";
    button.textContent = "显示";
  });
}

const PERMISSIONS = [
  ["工作台", true, true],
  ["清单", true, true],
  ["告警", true, true],
  ["环境", true, true],
  ["登记", false, true],
  ["确认告警", false, true],
  ["人员", false, true],
  ["权限", false, true]
];

function renderPermissions() {
  const body = document.querySelector("#permission-rows");
  body.replaceChildren();
  for (const [label, taker] of PERMISSIONS) {
    const row = document.createElement("tr");
    const ability = document.createElement("td");
    ability.className = "col-name";
    ability.textContent = label;
    row.append(ability, permissionCell(taker, false), permissionCell(true, true));
    body.append(row);
  }
}

function permissionCell(checked, locked) {
  const cell = document.createElement("td");
  cell.className = "col-level";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = checked;
  if (locked) {
    input.disabled = true;
  } else {
    input.addEventListener("change", () => showNote("还不能保存到服务器", true));
  }
  cell.append(input);
  return cell;
}

function showView(name) {
  view = name;
  document.querySelectorAll(".view").forEach((section) => {
    const on = section.dataset.view === name;
    section.hidden = !on;
    if (on) {
      section.classList.remove("is-entering");
      void section.offsetWidth;
      section.classList.add("is-entering");
    }
  });
  document.querySelectorAll(".nav[data-view]").forEach((button) => {
    button.classList.toggle("is-on", button.dataset.view === name);
  });
  const titles = { desk: "工作台", list: "清单", register: "登记", alarms: "告警", env: "环境", people: "人员", permissions: "权限" };
  document.querySelector("#view-title").textContent = titles[name] || "工作台";
  if (name === "people" || name === "permissions") {
    document.querySelector("#manage-menu").classList.add("is-open");
  }
}

async function refresh() {
  const list = await api("/api/reagents", { method: "GET" });
  items = list.body.items || [];
  const alarmBody = await api("/api/alarms", { method: "GET" });
  alarms = alarmBody.response.ok ? alarmBody.body.items || [] : [];
  const envBody = await api("/api/environment", { method: "GET" });
  env = envBody.response.ok ? envBody.body : null;
  if (role === "manager") {
    const peopleBody = await api("/api/accounts", { method: "GET" });
    people = peopleBody.response.ok ? peopleBody.body.items || [] : [];
  } else {
    people = [];
  }
  render();
}

async function removeReagent(item) {
  if (!window.confirm("从清单删除「" + item.name + "」？")) return;
  const result = await api("/api/reagents/" + item.id, { method: "DELETE" });
  showNote(result.body.message, result.body.result !== "ok");
  await refresh();
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
  const manager = me.role === "manager";
  document.querySelector("#who").textContent = `${me.name} · ${manager ? "管理人" : "取用人"}`;
  document.querySelectorAll(".manager-only").forEach((node) => {
    node.hidden = !manager;
  });
  showView("desk");
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
    storeRemembered(String(form.get("username") || ""), String(form.get("password") || ""), form.get("remember") === "on");
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
  if (result.body.result === "ok") {
    event.target.reset();
    syncRegisterMenus();
  }
  await refresh();
});

document.querySelectorAll("[data-view]").forEach((button) => {
  if (button.tagName !== "BUTTON") return;
  button.addEventListener("click", () => showView(button.dataset.view));
});

document.querySelector("#filter-q").addEventListener("input", (event) => {
  filters.q = event.target.value.trim();
  fillTable("list-rows", filteredItems(), "list-empty", true);
});

document.querySelector("#manage-toggle").addEventListener("click", () => {
  document.querySelector("#manage-menu").classList.toggle("is-open");
});

document.querySelector("#person-register-toggle").addEventListener("click", () => {
  const form = document.querySelector("#person-register");
  form.hidden = !form.hidden;
});

for (const id of ["person-role", "person-status"]) {
  document.querySelector("#" + id).addEventListener("submit", (event) => {
    event.preventDefault();
    showNote("还不能保存到服务器", true);
  });
}

document.querySelector("#person-register").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const name = String(form.get("name") || "").trim();
  const username = String(form.get("username") || "").trim();
  if (!name || !username) {
    showNote("姓名和账号不能为空", true);
    return;
  }
  const problem = passwordProblem(String(form.get("password") || ""), String(form.get("confirm") || ""));
  if (problem) {
    showNote(problem, true);
    return;
  }
  if (people.some((person) => person.username === username)) {
    showNote("这个账号已经有了", true);
    return;
  }
  showNote("还不能保存到服务器", true);
});

document.querySelector("#person-password").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const problem = passwordProblem(String(form.get("password") || ""), String(form.get("confirm") || ""));
  if (problem) {
    showNote(problem, true);
    return;
  }
  showNote("还不能保存到服务器", true);
});

document.querySelector("#person-reset").addEventListener("submit", (event) => {
  event.preventDefault();
  showNote("还不能保存到服务器", true);
});

document.querySelector("#self-password-toggle").addEventListener("click", () => {
  const form = document.querySelector("#self-password");
  form.hidden = !form.hidden;
});

document.querySelector("#self-password").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const current = String(form.get("current") || "");
  const password = String(form.get("password") || "");
  const confirm = String(form.get("confirm") || "");
  if (!current || !password || !confirm) {
    showNote("密码不能为空", true);
    return;
  }
  if (password !== confirm) {
    showNote("两次密码不一致", true);
    return;
  }
  showNote("还不能保存到服务器", true);
});

document.querySelectorAll(".secret-toggle").forEach((button) => {
  button.addEventListener("click", () => {
    const input = button.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "隐藏" : "显示";
  });
});

renderPermissions();

function closeMenus() {
  document.querySelectorAll(".menu-panel").forEach((panel) => {
    panel.hidden = true;
    panel.classList.remove("is-open");
  });
  document.querySelectorAll(".menu-trigger").forEach((button) => {
    button.setAttribute("aria-expanded", "false");
  });
}

function chooseMenu(menu, option) {
  const label = menu.querySelector(".menu-value");
  if (option.dataset.action) {
    const username = menu.closest("tr")?.dataset.username;
    const person = people.find((item) => item.username === username);
    if (person) openPerson(person, option.dataset.action);
    return;
  }
  if (menu.dataset.input) {
    const hidden = menu.parentElement.querySelector(`input[name="${menu.dataset.input}"]`);
    if (hidden) hidden.value = option.dataset.value;
  } else if (menu.dataset.filter) {
    filters[menu.dataset.filter] = option.dataset.value;
    fillTable("list-rows", filteredItems(), "list-empty", true);
  }
  if (label) label.textContent = option.textContent;
  menu.querySelectorAll("[data-value]").forEach((item) => {
    item.classList.toggle("is-on", item === option);
  });
}

document.addEventListener("click", (event) => {
  const trigger = event.target.closest(".menu-trigger");
  if (trigger) {
    const menu = trigger.closest(".menu");
    const panel = menu.querySelector(".menu-panel");
    const willOpen = panel.hidden;
    closeMenus();
    if (!willOpen) return;
    panel.hidden = false;
    panel.classList.add("is-open");
    trigger.setAttribute("aria-expanded", "true");
    return;
  }
  const option = event.target.closest(".menu-panel button");
  if (option) {
    chooseMenu(option.closest(".menu"), option);
    closeMenus();
    return;
  }
  closeMenus();
});

function syncRegisterMenus() {
  document.querySelectorAll("#register-form .menu").forEach((menu) => {
    const hidden = menu.parentElement.querySelector(`input[name="${menu.dataset.input}"]`);
    const match = menu.querySelector(`[data-value="${CSS.escape(hidden.value)}"]`);
    if (match) menu.querySelector(".menu-value").textContent = match.textContent;
  });
}

document.querySelector("#person-password-reveal").addEventListener("click", () => {
  const node = document.querySelector("#person-fact-password");
  const button = document.querySelector("#person-password-reveal");
  if (node.dataset.shown === "true") {
    maskPersonPassword();
    return;
  }
  node.textContent = "密码已隐藏，无法直接查看";
  node.dataset.shown = "true";
  button.textContent = "隐藏";
});

document.querySelector("#person-view-password").addEventListener("click", () => {
  const person = people.find((item) => item.username === personFocus?.username);
  if (person) openPerson(person, "password");
});

document.querySelector("#person-view-reset").addEventListener("click", () => {
  const person = people.find((item) => item.username === personFocus?.username);
  if (person) openPerson(person, "reset");
});

applyRemembered();

api("/api/auth/me", { method: "GET" }).then((result) => {
  if (result.response.ok) enter(result.body);
}).catch(() => {});
