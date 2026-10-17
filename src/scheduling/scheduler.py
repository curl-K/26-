"""调度模块。

输入是仓管员动作、俯视读数和到位报告。输出是登记、任务状态、指定了哪辆车、
这辆车能不能开，以及告警。俯视读数只说明货物编号的中心在货位、场外、车斗
或没有读到；已取、已放和告警由本模块判断。
"""

from __future__ import annotations

from dataclasses import dataclass, field

OUTSIDE = "场外"
UNSEEN_LIMIT = 3.0

_CELLS = range(1, 10)
_VEHICLES = (1, 2)


def planned_route(origin: int | str, dest: int | str) -> tuple[int | str, ...]:
    """沿格子中心、只走横竖的最短折线，先横后竖。场外只接 2 号。"""
    if origin == dest:
        return (origin,)
    points: list[int | str] = []
    if origin == OUTSIDE:
        points.append(OUTSIDE)
        start = 2
    else:
        start = origin
    if dest == OUTSIDE:
        points.extend(_orthogonal(start, 2))
        points.append(OUTSIDE)
    else:
        points.extend(_orthogonal(start, dest))
    return tuple(_dedupe(points))


def routes_cross(left: tuple[int | str, ...], right: tuple[int | str, ...]) -> bool:
    """两条折线共用一个格子，或线段相交。"""
    if not left or not right:
        return False
    left_cells = {point for point in left if isinstance(point, int)}
    right_cells = {point for point in right if isinstance(point, int)}
    if left_cells & right_cells:
        return True
    left_segments = list(zip(left, left[1:]))
    right_segments = list(zip(right, right[1:]))
    return any(
        _segments_intersect(a, b, c, d)
        for a, b in left_segments
        for c, d in right_segments
    )


def _coord(point: int | str) -> tuple[int, int]:
    if point == OUTSIDE:
        return (1, -1)
    if not isinstance(point, int):
        raise ValueError(f"未知地点 {point!r}")
    index = point - 1
    return (index % 3, index // 3)


def _cell_at(col: int, row: int) -> int:
    return row * 3 + col + 1


def _orthogonal(start: int, end: int) -> list[int]:
    col, row = _coord(start)
    target_col, target_row = _coord(end)
    path = [start]
    step = 1 if target_col > col else -1
    while col != target_col:
        col += step
        path.append(_cell_at(col, row))
    step = 1 if target_row > row else -1
    while row != target_row:
        row += step
        path.append(_cell_at(col, row))
    return path


def _dedupe(points: list[int | str]) -> list[int | str]:
    deduped: list[int | str] = []
    for point in points:
        if not deduped or deduped[-1] != point:
            deduped.append(point)
    return deduped


def _segments_intersect(
    start_a: int | str,
    end_a: int | str,
    start_b: int | str,
    end_b: int | str,
) -> bool:
    a1, a2 = _coord(start_a), _coord(end_a)
    b1, b2 = _coord(start_b), _coord(end_b)

    def orient(p: tuple[int, int], q: tuple[int, int], r: tuple[int, int]) -> int:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_segment(p: tuple[int, int], q: tuple[int, int], r: tuple[int, int]) -> bool:
        return (
            min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
            and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
        )

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)
    if o1 == 0 and on_segment(a1, b1, a2):
        return True
    if o2 == 0 and on_segment(a1, b2, a2):
        return True
    if o3 == 0 and on_segment(b1, a1, b2):
        return True
    if o4 == 0 and on_segment(b1, a2, b2):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


@dataclass(frozen=True)
class Bed:
    """货物编号的中心落在这辆运输车的车斗里。"""

    vehicle: int

    def __post_init__(self) -> None:
        if self.vehicle not in _VEHICLES:
            raise ValueError("只有车 1 和车 2")


@dataclass(frozen=True)
class DispatchResult:
    accepted: bool
    task_id: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class TaskState:
    id: int
    kind: str
    number: str
    status: str
    vehicle: int | None
    pickup: int | str | None
    drop: int | str
    route: tuple[int | str, ...]
    end_reason: str | None = None


@dataclass(frozen=True)
class VehicleState:
    id: int
    may_drive: bool
    target: int | str | None
    task_id: int | None


@dataclass(frozen=True)
class AlertState:
    kind: str
    number: str | None = None
    cell: int | None = None
    awaits_confirmation: bool = False


@dataclass
class _Vehicle:
    id: int
    task_id: int | None = None
    may_drive: bool = False
    target: int | str | None = None
    position: int | str | None = None


@dataclass
class _Task:
    id: int
    kind: str
    number: str
    pickup: int | str | None
    drop: int | str
    name_proposal: str | None
    phase: str
    created_seq: int
    vehicle: int | None = None
    route: tuple[int | str, ...] = ()
    checked: bool = False
    check_passed_at: float | None = None
    origin_arrived_at: float | None = None
    picked_up: bool = False
    picked_up_seq: int | None = None
    placed: bool = False
    end_reason: str | None = None
    slow_alerted: bool = False


@dataclass
class _Alert:
    kind: str
    number: str | None = None
    cell: int | None = None
    awaits_confirmation: bool = False
    active: bool = True

    def view(self) -> AlertState:
        return AlertState(
            kind=self.kind,
            number=self.number,
            cell=self.cell,
            awaits_confirmation=self.awaits_confirmation,
        )


@dataclass
class _Hold:
    number: str
    cell: int
    vehicle: int


@dataclass
class _Multi:
    original: str | None
    extras: set[str] = field(default_factory=set)


class Scheduler:
    """边缘节点 edge1 上的调度：登记、任务、告警，以及每辆车能不能开。"""

    edge_id = "edge1"

    def __init__(self) -> None:
        self._now = 0.0
        self._cloud_online = True
        self._names: dict[str, str] = {}
        self._registered: dict[str, int] = {}
        self._on_vehicle: dict[str, int] = {}
        self._obs: dict[str, int | str | Bed | None] = {}
        self._unseen_since: dict[str, float] = {}
        self._suppress_unseen_outbound: set[str] = set()
        self._tasks: list[_Task] = []
        self._vehicles = {vehicle_id: _Vehicle(vehicle_id) for vehicle_id in _VEHICLES}
        self._alerts: list[_Alert] = []
        self._holds: list[_Hold] = []
        self._multi: dict[int, _Multi] = {}
        self._next_task_id = 1
        self._next_seq = 1

    def bind_name(self, number: str, name: str) -> DispatchResult:
        cleaned = _required_text(name)
        if cleaned is None:
            return DispatchResult(False, reason="缺少货物名称")
        self._names[number] = cleaned
        return DispatchResult(True)

    def transfer(self, number: str, drop_cell: int) -> DispatchResult:
        refused = self._refuse_common(drop_cell)
        if refused is not None:
            return refused
        if number not in self._registered:
            return DispatchResult(False, reason="货物未登记")
        if self._unfinished_for(number) is not None:
            return DispatchResult(False, reason="该货物已有未结束任务")
        pickup = self._registered[number]
        if drop_cell == pickup or not self.cell_free(drop_cell):
            return DispatchResult(False, reason="放货货位不是空闲")
        if self._pickup_blocked(pickup, number):
            return DispatchResult(False, reason="取货货位已被占用")
        return self._enqueue("移库", number, pickup, drop_cell, None)

    def inbound(self, number: str, name: str, drop_cell: int) -> DispatchResult:
        if not self._cloud_online:
            return DispatchResult(False, reason="断云")
        cleaned = _required_text(name)
        if cleaned is None:
            return DispatchResult(False, reason="缺少货物名称")
        if not _valid_cell(drop_cell):
            return DispatchResult(False, reason="货位无效")
        if not self.outside_free():
            return DispatchResult(False, reason="场外已被占用")
        if not self.cell_free(drop_cell):
            return DispatchResult(False, reason="放货货位不是空闲")
        if self._unfinished_for(number) is not None:
            return DispatchResult(False, reason="该货物已有未结束任务")
        if number in self._registered or number in self._on_vehicle:
            return DispatchResult(False, reason="货物已登记")
        return self._enqueue("入库", number, OUTSIDE, drop_cell, cleaned)

    def outbound(self, number: str) -> DispatchResult:
        if not self._cloud_online:
            return DispatchResult(False, reason="断云")
        if not self.outside_free():
            return DispatchResult(False, reason="场外已被占用")
        if number not in self._registered:
            return DispatchResult(False, reason="货物未登记")
        if self._unfinished_for(number) is not None:
            return DispatchResult(False, reason="该货物已有未结束任务")
        pickup = self._registered[number]
        if self._pickup_blocked(pickup, number):
            return DispatchResult(False, reason="取货货位已被占用")
        return self._enqueue("出库", number, pickup, OUTSIDE, None)

    def confirm_wrong_cell(self, number: str) -> None:
        for alert in self._alerts:
            if alert.active and alert.kind == "放错格" and alert.number == number:
                alert.active = False

    def disconnect(self) -> None:
        self._cloud_online = False

    def reconnect(self) -> None:
        self._cloud_online = True
        self._pump()

    def see(self, number: str, where: int | str | Bed | None) -> None:
        _validate_sight(where)
        self._note(number, where)
        self._sync_multi()
        task = self._unfinished_for(number)
        if self._in_multi(number):
            if (
                task is not None
                and task.phase == "at_origin"
                and not task.checked
                and task.kind != "入库"
            ):
                self._fail_check(task)
            return
        if task is not None:
            self._on_task_sight(task, where)
        else:
            self._on_idle_sight(number, where)

    def arrive(self, vehicle_id: int, where: int | str) -> None:
        if vehicle_id not in _VEHICLES or not _valid_stop(where):
            return
        vehicle = self._vehicles[vehicle_id]
        if not vehicle.may_drive or vehicle.target != where or vehicle.task_id is None:
            return
        task = self._task(vehicle.task_id)
        vehicle.position = where
        vehicle.may_drive = False
        vehicle.target = None
        if task.phase == "to_origin":
            task.phase = "at_origin"
            task.origin_arrived_at = self._now
            self._evaluate_origin(task)
        elif task.phase == "to_dest":
            self._complete_arrival(task)

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("时间不能倒退")
        self._now += seconds
        self._expire_unseen()
        self._expire_checks()
        self._expire_slow_pickups()

    def cell_of(self, number: str) -> int | None:
        return self._registered.get(number)

    def vehicle_of(self, number: str) -> int | None:
        if number in self._registered:
            return None
        return self._on_vehicle.get(number)

    def name_of(self, number: str) -> str | None:
        return self._names.get(number)

    def cell_free(self, cell: int) -> bool:
        if cell in self._multi:
            return False
        if cell in self._registered.values():
            return False
        if any(hold.cell == cell for hold in self._holds):
            return False
        for task in self._tasks:
            if task.phase == "ended":
                continue
            if task.drop == cell or task.pickup == cell:
                return False
        return True

    def outside_free(self) -> bool:
        return not any(
            task.phase != "ended" and task.kind in ("入库", "出库") for task in self._tasks
        )

    def cloud_online(self) -> bool:
        return self._cloud_online

    def console_status(self) -> str:
        return "在线" if self._cloud_online else "离线"

    def task(self, task_id: int) -> TaskState:
        return self._view(self._task(task_id))

    def tasks(self) -> list[TaskState]:
        return [self._view(task) for task in self._tasks]

    def vehicle(self, vehicle_id: int) -> VehicleState:
        vehicle = self._vehicles[vehicle_id]
        return VehicleState(
            id=vehicle.id,
            may_drive=vehicle.may_drive,
            target=vehicle.target,
            task_id=vehicle.task_id,
        )

    def alerts(self) -> list[AlertState]:
        return [alert.view() for alert in self._alerts if alert.active]

    def console_alerts(self) -> list[AlertState]:
        if not self._cloud_online:
            return []
        return self.alerts()

    def _refuse_common(self, drop_cell: int) -> DispatchResult | None:
        if not self._cloud_online:
            return DispatchResult(False, reason="断云")
        if not _valid_cell(drop_cell):
            return DispatchResult(False, reason="货位无效")
        return None

    def _enqueue(
        self,
        kind: str,
        number: str,
        pickup: int | str | None,
        drop: int | str,
        name_proposal: str | None,
    ) -> DispatchResult:
        task = _Task(
            id=self._next_task_id,
            kind=kind,
            number=number,
            pickup=pickup,
            drop=drop,
            name_proposal=name_proposal,
            phase="pending",
            created_seq=self._next_seq,
            route=planned_route(pickup, drop) if pickup is not None else (),
        )
        self._next_task_id += 1
        self._next_seq += 1
        self._tasks.append(task)
        self._pump()
        return DispatchResult(True, task_id=task.id)

    def _pump(self) -> None:
        if not self._cloud_online:
            return
        while True:
            vehicle = self._idle_vehicle()
            pending = [task for task in self._tasks if task.phase == "pending"]
            if vehicle is None or not pending:
                return
            head = pending[0]
            if not self._assignable(head):
                return
            self._assign(head, vehicle)

    def _assignable(self, task: _Task) -> bool:
        if task.kind in ("移库", "出库"):
            return task.number in self._registered
        return task.kind == "入库"

    def _assign(self, task: _Task, vehicle: _Vehicle) -> None:
        if task.kind in ("移库", "出库"):
            task.pickup = self._registered[task.number]
        assert task.pickup is not None
        task.route = planned_route(task.pickup, task.drop)
        task.vehicle = vehicle.id
        task.phase = "to_origin"
        vehicle.task_id = task.id
        vehicle.may_drive = True
        vehicle.target = task.pickup

    def _idle_vehicle(self) -> _Vehicle | None:
        if self._vehicles[1].task_id is None:
            return self._vehicles[1]
        if self._vehicles[2].task_id is None:
            return self._vehicles[2]
        return None

    def _note(self, number: str, where: int | str | Bed | None) -> None:
        self._obs[number] = where
        if where is None:
            self._unseen_since.setdefault(number, self._now)
        else:
            self._unseen_since.pop(number, None)
            self._suppress_unseen_outbound.discard(number)

    def _on_idle_sight(self, number: str, where: int | str | Bed | None) -> None:
        if isinstance(where, int) and where in self._multi:
            return
        hold = self._hold_for(number)
        if isinstance(where, int):
            if hold is not None:
                if where == hold.cell:
                    self._register_cell(number, where, unauthorized=False)
                else:
                    self._register_cell(number, where, unauthorized=False)
                    self._raise("放错格", number=number, cell=where, confirm=True)
                return
            if self._registered.get(number) == where:
                return
            fresh = number not in self._registered and number not in self._on_vehicle
            self._register_cell(number, where, unauthorized=fresh)
            return
        if where is None or hold is not None:
            return
        if isinstance(where, Bed) and self._on_vehicle.get(number) == where.vehicle:
            return
        if number in self._registered or number in self._on_vehicle:
            self._drop_registration(number, via_multi=False, outbound_alert=False)

    def _on_task_sight(self, task: _Task, where: int | str | Bed | None) -> None:
        if where is None or task.phase == "ended":
            return
        if isinstance(where, int) and where in self._multi:
            return
        if task.picked_up:
            self._sight_after_pickup(task, where)
            return
        if isinstance(where, Bed) and where.vehicle == task.vehicle:
            if task.phase in ("at_origin", "waiting_pickup"):
                if not task.checked:
                    self._pass_check(task)
                if task.checked and not task.picked_up:
                    self._pick_up(task)
            return
        if isinstance(where, int):
            if task.kind == "入库":
                self._wrong_before_pickup(task, where)
                return
            if not task.checked:
                self._register_cell(task.number, where, unauthorized=False)
                if task.phase == "at_origin" and where == task.pickup:
                    self._pass_check(task)
                elif task.phase == "at_origin" and where != task.pickup:
                    self._fail_check(task)
                return
            if where == task.pickup:
                self._register_cell(task.number, where, unauthorized=False)
                return
            self._wrong_before_pickup(task, where)
            return
        if where == OUTSIDE and task.phase == "at_origin" and not task.checked:
            if task.kind == "入库":
                self._pass_check(task)
            else:
                self._fail_check(task)

    def _sight_after_pickup(self, task: _Task, where: int | str | Bed) -> None:
        if isinstance(where, Bed) and where.vehicle == task.vehicle:
            return
        if not isinstance(where, int):
            return
        if task.kind != "出库" and where == task.drop:
            self._register_cell(task.number, where, unauthorized=False)
            task.placed = True
            return
        self._wrong_after_pickup(task, where)

    def _evaluate_origin(self, task: _Task) -> None:
        if task.phase == "ended":
            return
        if task.checked:
            self._maybe_pick_up_from_observation(task)
            return
        if task.kind != "入库" and isinstance(task.pickup, int) and task.pickup in self._multi:
            self._fail_check(task)
            return
        where = self._obs.get(task.number)
        if task.kind == "入库":
            if where == OUTSIDE or _in_bed(where, task.vehicle):
                self._pass_check(task)
                if _in_bed(where, task.vehicle):
                    self._pick_up(task)
            elif isinstance(where, int):
                self._wrong_before_pickup(task, where)
            return
        if where == task.pickup or _in_bed(where, task.vehicle):
            self._pass_check(task)
            if _in_bed(where, task.vehicle):
                self._pick_up(task)
            return
        if isinstance(where, int) or where == OUTSIDE:
            self._fail_check(task)

    def _maybe_pick_up_from_observation(self, task: _Task) -> None:
        where = self._obs.get(task.number)
        if task.checked and not task.picked_up and _in_bed(where, task.vehicle):
            self._pick_up(task)

    def _pass_check(self, task: _Task) -> None:
        if task.checked or task.phase == "ended":
            return
        task.checked = True
        task.check_passed_at = self._now
        task.phase = "waiting_pickup"
        if task.kind == "入库" and task.name_proposal is not None:
            self._names[task.number] = task.name_proposal
        if task.vehicle is not None:
            vehicle = self._vehicles[task.vehicle]
            vehicle.may_drive = False
            vehicle.target = None

    def _fail_check(self, task: _Task) -> None:
        if task.phase == "ended":
            return
        cell = task.pickup if isinstance(task.pickup, int) else None
        self._raise("核对不符", number=task.number, cell=cell)
        self._finish(task, reason="核对不符", hold_drop=False)

    def _wrong_before_pickup(self, task: _Task, cell: int) -> None:
        self._register_cell(task.number, cell, unauthorized=False)
        self._raise("放错格", number=task.number, cell=cell, confirm=True)
        if task.vehicle is None:
            return
        if task.phase in ("at_origin", "waiting_pickup"):
            vehicle = self._vehicles[task.vehicle]
            vehicle.may_drive = False
            vehicle.target = None

    def _wrong_after_pickup(self, task: _Task, cell: int) -> None:
        self._register_cell(task.number, cell, unauthorized=False)
        self._raise("放错格", number=task.number, cell=cell, confirm=True)
        if task.phase != "ended":
            self._finish(task, reason="放错格", hold_drop=False)

    def _pick_up(self, task: _Task) -> None:
        if task.picked_up or not task.checked or task.phase == "ended":
            return
        task.picked_up = True
        task.picked_up_seq = self._next_seq
        self._next_seq += 1
        self._registered.pop(task.number, None)
        if task.vehicle is not None:
            self._on_vehicle[task.number] = task.vehicle
        self._suppress_unseen_outbound.discard(task.number)
        task.phase = "to_dest"
        self._update_drive(task)

    def _update_drive(self, task: _Task) -> None:
        if not task.picked_up or task.phase == "ended" or task.vehicle is None:
            return
        other = self._other_driving(task)
        if (
            other is not None
            and other.picked_up
            and other.picked_up_seq is not None
            and task.picked_up_seq is not None
            and other.picked_up_seq < task.picked_up_seq
            and routes_cross(task.route, other.route)
        ):
            task.phase = "waiting_path"
            vehicle = self._vehicles[task.vehicle]
            vehicle.may_drive = False
            vehicle.target = None
            return
        task.phase = "to_dest"
        vehicle = self._vehicles[task.vehicle]
        vehicle.may_drive = True
        vehicle.target = task.drop

    def _complete_arrival(self, task: _Task) -> None:
        if task.kind == "出库":
            self._registered.pop(task.number, None)
            self._on_vehicle.pop(task.number, None)
            self._remove_hold(task.number)
            self._finish(task, reason="已到位", hold_drop=False)
            return
        already_placed = (
            isinstance(task.drop, int) and self._registered.get(task.number) == task.drop
        )
        task.placed = already_placed
        self._finish(task, reason="已到位", hold_drop=not already_placed)

    def _finish(self, task: _Task, *, reason: str, hold_drop: bool) -> None:
        if task.phase == "ended":
            return
        if (
            hold_drop
            and not task.placed
            and isinstance(task.drop, int)
            and task.vehicle is not None
        ):
            self._remove_hold(task.number)
            self._holds.append(_Hold(task.number, task.drop, task.vehicle))
            if task.number not in self._registered:
                self._on_vehicle[task.number] = task.vehicle
        task.phase = "ended"
        task.end_reason = reason
        if task.vehicle is not None:
            vehicle = self._vehicles[task.vehicle]
            if vehicle.task_id == task.id:
                vehicle.task_id = None
                vehicle.may_drive = False
                vehicle.target = None
        self._release_path_waits()
        self._pump()

    def _release_path_waits(self) -> None:
        for task in self._tasks:
            if task.phase == "waiting_path":
                self._update_drive(task)

    def _expire_unseen(self) -> None:
        expired = [
            number
            for number, since in self._unseen_since.items()
            if self._now - since >= UNSEEN_LIMIT
        ]
        for number in expired:
            if self._waiting_for_pickup(number):
                continue
            registered = number in self._registered or number in self._on_vehicle
            if not registered:
                continue
            if (
                number in self._suppress_unseen_outbound
                and number not in self._registered
                and number not in self._on_vehicle
            ):
                continue
            self._drop_registration(number, via_multi=False, outbound_alert=True)

    def _expire_checks(self) -> None:
        for task in list(self._tasks):
            if task.phase != "at_origin" or task.checked or task.origin_arrived_at is None:
                continue
            if self._now - task.origin_arrived_at < UNSEEN_LIMIT:
                continue
            if task.kind == "入库" and isinstance(self._obs.get(task.number), int):
                continue
            self._fail_check(task)

    def _expire_slow_pickups(self) -> None:
        for task in self._tasks:
            if task.phase == "ended" or not task.checked or task.picked_up or task.slow_alerted:
                continue
            if task.check_passed_at is None:
                continue
            if self._now - task.check_passed_at >= UNSEEN_LIMIT:
                task.slow_alerted = True
                self._raise("迟迟未已取", number=task.number)

    def _sync_multi(self) -> None:
        visible: dict[int, set[str]] = {cell: set() for cell in _CELLS}
        for number, where in self._obs.items():
            if isinstance(where, int) and where in visible:
                visible[where].add(number)
        for cell in _CELLS:
            codes = visible[cell]
            state = self._multi.get(cell)
            if len(codes) >= 2:
                self._enter_multi(cell, codes)
            elif state is not None:
                self._leave_multi(cell, codes, state)

    def _enter_multi(self, cell: int, codes: set[str]) -> None:
        state = self._multi.get(cell)
        if state is None:
            original = next(
                (code for code in codes if self._registered.get(code) == cell),
                None,
            )
            state = _Multi(original)
            self._multi[cell] = state
            self._raise("一格多货", cell=cell)
        for code in codes:
            if state.original is not None and code == state.original:
                if self._registered.get(code) == cell or code in self._on_vehicle:
                    self._drop_registration(code, via_multi=True, outbound_alert=False)
                continue
            if code in self._registered or code in self._on_vehicle:
                self._drop_registration(code, via_multi=True, outbound_alert=False)
            state.extras.add(code)
            self._raise("未经入库", number=code, cell=cell)

    def _leave_multi(self, cell: int, codes: set[str], state: _Multi) -> None:
        self._clear_alert("一格多货", cell=cell)
        self._multi.pop(cell, None)
        if len(codes) == 1:
            only = next(iter(codes))
            restore_original = state.original is not None and only == state.original
            self._register_cell(only, cell, unauthorized=not restore_original)
            for extra in state.extras:
                if extra != only and extra not in self._registered:
                    self._clear_alert("未经入库", number=extra)
            return
        for extra in state.extras:
            if extra not in self._registered:
                self._clear_alert("未经入库", number=extra)

    def _register_cell(self, number: str, cell: int, *, unauthorized: bool) -> None:
        self._on_vehicle.pop(number, None)
        self._registered[number] = cell
        self._suppress_unseen_outbound.discard(number)
        self._remove_hold(number)
        if unauthorized:
            self._raise("未经入库", number=number, cell=cell)
        self._retarget_pending(number)
        self._pump()

    def _drop_registration(
        self,
        number: str,
        *,
        via_multi: bool,
        outbound_alert: bool,
    ) -> None:
        cell = self._registered.pop(number, None)
        self._on_vehicle.pop(number, None)
        self._remove_hold(number)
        if via_multi:
            self._suppress_unseen_outbound.add(number)
        if outbound_alert:
            self._raise("未经出库", number=number, cell=cell)
            task = self._unfinished_for(number)
            if task is not None and not self._waiting_for_pickup(number):
                self._finish(task, reason="未经出库", hold_drop=False)
            return
        self._retarget_pending(number)

    def _retarget_pending(self, number: str) -> None:
        for task in self._tasks:
            if task.phase != "pending" or task.number != number:
                continue
            if task.kind not in ("移库", "出库"):
                continue
            task.pickup = self._registered.get(number)
            task.route = planned_route(task.pickup, task.drop) if task.pickup is not None else ()

    def _waiting_for_pickup(self, number: str) -> bool:
        task = self._unfinished_for(number)
        return task is not None and task.checked and not task.picked_up

    def _in_multi(self, number: str) -> bool:
        where = self._obs.get(number)
        return isinstance(where, int) and where in self._multi

    def _hold_for(self, number: str) -> _Hold | None:
        for hold in self._holds:
            if hold.number == number:
                return hold
        return None

    def _remove_hold(self, number: str) -> None:
        self._holds = [hold for hold in self._holds if hold.number != number]

    def _unfinished_for(self, number: str) -> _Task | None:
        for task in self._tasks:
            if task.number == number and task.phase != "ended":
                return task
        return None

    def _other_driving(self, task: _Task) -> _Task | None:
        for other in self._tasks:
            if other.id == task.id or other.phase in ("ended", "pending") or other.vehicle is None:
                continue
            return other
        return None

    def _pickup_blocked(self, pickup: int, number: str) -> bool:
        for task in self._tasks:
            if task.phase == "ended":
                continue
            if task.drop == pickup:
                return True
        return any(hold.cell == pickup and hold.number != number for hold in self._holds)

    def _task(self, task_id: int) -> _Task:
        for task in self._tasks:
            if task.id == task_id:
                return task
        raise KeyError(task_id)

    def _view(self, task: _Task) -> TaskState:
        return TaskState(
            id=task.id,
            kind=task.kind,
            number=task.number,
            status=_status(task.phase),
            vehicle=task.vehicle,
            pickup=task.pickup,
            drop=task.drop,
            route=task.route,
            end_reason=task.end_reason,
        )

    def _raise(
        self,
        kind: str,
        *,
        number: str | None = None,
        cell: int | None = None,
        confirm: bool = False,
    ) -> None:
        for alert in self._alerts:
            if not alert.active or alert.kind != kind:
                continue
            if kind == "一格多货" and alert.cell == cell:
                return
            if kind != "一格多货" and alert.number == number:
                alert.cell = cell
                alert.awaits_confirmation = alert.awaits_confirmation or confirm
                return
        self._alerts.append(
            _Alert(
                kind=kind,
                number=number,
                cell=cell,
                awaits_confirmation=confirm,
            )
        )

    def _clear_alert(
        self,
        kind: str,
        *,
        number: str | None = None,
        cell: int | None = None,
    ) -> None:
        for alert in self._alerts:
            if not alert.active or alert.kind != kind:
                continue
            if number is not None and alert.number != number:
                continue
            if cell is not None and alert.cell != cell:
                continue
            alert.active = False


def _status(phase: str) -> str:
    if phase == "ended":
        return "已结束"
    if phase == "pending":
        return "待派"
    if phase == "waiting_path":
        return "等路"
    return "执行中"


def _required_text(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _valid_cell(cell: object) -> bool:
    return isinstance(cell, int) and not isinstance(cell, bool) and cell in _CELLS


def _valid_stop(where: object) -> bool:
    return where == OUTSIDE or _valid_cell(where)


def _validate_sight(where: int | str | Bed | None) -> None:
    if where is None or isinstance(where, Bed) or _valid_stop(where):
        return
    raise ValueError(f"无法识别的读数 {where!r}")


def _in_bed(where: object, vehicle: int | None) -> bool:
    return isinstance(where, Bed) and vehicle is not None and where.vehicle == vehicle
