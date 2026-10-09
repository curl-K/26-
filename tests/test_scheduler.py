"""调度模块的用户故事。

测试只提交仓管员动作、视觉读数和到位报告，然后查看登记、任务、
指定的车、能不能开，以及告警。
"""

from scheduling import OUTSIDE, Bed, Scheduler, planned_route


def test_九宫格先横后竖_1到9是1_2_3_6_9():
    assert planned_route(1, 9) == (1, 2, 3, 6, 9)
    assert planned_route(9, 1) == (9, 8, 7, 4, 1)
    assert planned_route(2, 9) == (2, 3, 6, 9)
    assert planned_route(9, 2) == (9, 8, 5, 2)


def test_入库和出库都经过2号():
    assert planned_route(OUTSIDE, 5) == (OUTSIDE, 2, 5)
    assert planned_route(5, OUTSIDE) == (5, 2, OUTSIDE)
    assert planned_route(OUTSIDE, 9) == (OUTSIDE, 2, 3, 6, 9)
    assert planned_route(1, OUTSIDE) == (1, 2, OUTSIDE)


def test_名称绑定不决定格子_格子只由读数写入():
    scheduler = Scheduler()
    scheduler.bind_name("A-01", "轴承")

    assert scheduler.cell_of("A-01") is None
    assert scheduler.name_of("A-01") == "轴承"

    scheduler.see("A-01", 4)

    assert scheduler.cell_of("A-01") == 4
    assert scheduler.name_of("A-01") == "轴承"


def test_只在场外看到的编号不登记也不占货位():
    scheduler = Scheduler()
    scheduler.see("外-1", OUTSIDE)
    scheduler.advance(5)

    assert scheduler.cell_of("外-1") is None
    assert scheduler.vehicle_of("外-1") is None
    assert scheduler.alerts() == []
    assert scheduler.cell_free(2)
    assert scheduler.outside_free()
    assert not scheduler.transfer("外-1", 5).accepted


def test_没走进库也登记并告警未经入库_名称不变_之后仍可移库():
    scheduler = Scheduler()
    scheduler.bind_name("A-01", "轴承")
    scheduler.see("A-01", 6)

    assert scheduler.cell_of("A-01") == 6
    assert scheduler.name_of("A-01") == "轴承"
    assert has_alert(scheduler, "未经入库", number="A-01", cell=6)
    assert scheduler.transfer("A-01", 1).accepted


def test_没有名称时未经入库也不留下名称():
    scheduler = Scheduler()
    scheduler.see("裸-1", 2)

    assert scheduler.cell_of("裸-1") == 2
    assert scheduler.name_of("裸-1") is None
    assert has_alert(scheduler, "未经入库", number="裸-1")


def test_一格两个编号都不登记_原件离开不报未经出库_后放的报未经入库():
    scheduler = Scheduler()
    scheduler.bind_name("A-01", "轴承")
    scheduler.see("A-01", 4)
    scheduler.see("B-02", 4)

    assert scheduler.cell_of("A-01") is None
    assert scheduler.cell_of("B-02") is None
    assert not scheduler.cell_free(4)
    assert has_alert(scheduler, "一格多货", cell=4)
    assert has_alert(scheduler, "未经入库", number="B-02")
    assert not has_alert(scheduler, "未经出库", number="A-01")
    assert scheduler.name_of("A-01") == "轴承"
    assert not scheduler.transfer("A-01", 5).accepted
    assert not scheduler.outbound("B-02").accepted


def test_一格又只剩原来那一件时恢复登记并取消后放件的未经入库():
    scheduler = Scheduler()
    scheduler.see("A-01", 4)
    scheduler.see("B-02", 4)
    scheduler.see("B-02", None)

    assert scheduler.cell_of("A-01") == 4
    assert scheduler.cell_of("B-02") is None
    assert not has_alert(scheduler, "一格多货")
    assert not has_alert(scheduler, "未经入库", number="B-02")
    assert scheduler.transfer("A-01", 9).accepted


def test_后放的那一件变成这一格唯一编号时按未经入库登记():
    scheduler = Scheduler()
    scheduler.see("A-01", 4)
    scheduler.see("B-02", 4)
    scheduler.see("A-01", None)

    assert scheduler.cell_of("B-02") == 4
    assert scheduler.cell_of("A-01") is None
    assert has_alert(scheduler, "未经入库", number="B-02", cell=4)
    assert not has_alert(scheduler, "未经出库", number="A-01")
    assert not has_alert(scheduler, "一格多货")
    assert scheduler.cell_free(4) is False


def test_同一格短暂丢失再读到_登记和告警不变():
    scheduler = Scheduler()
    scheduler.see("A-01", 3)
    before = scheduler.alerts()

    scheduler.see("A-01", None)
    scheduler.advance(2.9)
    scheduler.see("A-01", 3)

    assert scheduler.cell_of("A-01") == 3
    assert not has_alert(scheduler, "未经出库")
    assert scheduler.alerts() == before


def test_换到另一格是登记跟着走_不是未经出库():
    scheduler = Scheduler()
    scheduler.see("A-01", 1)
    scheduler.see("A-01", 8)

    assert scheduler.cell_of("A-01") == 8
    assert scheduler.cell_free(1)
    assert not has_alert(scheduler, "未经出库")


def test_连续三秒哪里都读不到就离开登记_名称保留并告警未经出库():
    scheduler = Scheduler()
    scheduler.bind_name("A-01", "轴承")
    scheduler.see("A-01", 7)
    scheduler.see("A-01", None)
    scheduler.advance(2.9)

    assert scheduler.cell_of("A-01") == 7
    assert not has_alert(scheduler, "未经出库")

    scheduler.advance(0.1)

    assert scheduler.cell_of("A-01") is None
    assert scheduler.cell_free(7)
    assert scheduler.name_of("A-01") == "轴承"
    assert has_alert(scheduler, "未经出库", number="A-01", cell=7)


def test_两辆车都在待命时指定车1_车1忙时指定车2_都忙则待派():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 3)
    scheduler.see("丙", 7)
    first = scheduler.transfer("甲", 4)
    second = scheduler.transfer("乙", 6)
    third = scheduler.transfer("丙", 9)

    assert scheduler.task(first.task_id).vehicle == 1
    assert scheduler.task(first.task_id).status == "执行中"
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 1
    assert scheduler.task(second.task_id).vehicle == 2
    assert scheduler.vehicle(2).target == 3
    assert scheduler.task(third.task_id).status == "待派"
    assert scheduler.task(third.task_id).vehicle is None
    assert scheduler.task(first.task_id).route == (1, 4)
    assert scheduler.task(second.task_id).route == (3, 6)


def test_移库只选货物和放货货位_未登记或放货货位不空则拒绝():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 5)

    assert not scheduler.transfer("没有", 2).accepted
    assert scheduler.transfer("没有", 2).reason == "货物未登记"
    assert not scheduler.transfer("甲", 5).accepted
    assert scheduler.transfer("甲", 5).reason == "放货货位不是空闲"
    assert not scheduler.transfer("甲", 1).accepted
    accepted = scheduler.transfer("甲", 2)
    assert accepted.accepted
    assert scheduler.task(accepted.task_id).kind == "移库"
    assert scheduler.task(accepted.task_id).pickup == 1
    assert scheduler.task(accepted.task_id).drop == 2


def test_核对通过前不能开向目的地_丢一帧又回到取货点不算已取():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 2)
    scheduler.arrive(1, 1)

    assert scheduler.task(task.task_id).status == "执行中"
    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.vehicle_of("甲") is None

    scheduler.see("甲", None)
    scheduler.see("甲", 1)

    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.vehicle_of("甲") is None
    assert scheduler.cell_of("甲") == 1
    assert scheduler.task(task.task_id).status == "执行中"


def test_编号中心落进指定车的车斗才已取_然后才开向放货货位():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 4)
    scheduler.arrive(1, 1)
    scheduler.see("甲", Bed(2))

    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.vehicle_of("甲") is None

    scheduler.see("甲", Bed(1))

    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.cell_of("甲") is None
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 4
    assert scheduler.task(task.task_id).route == (1, 4)


def test_等已取时三秒读不到不按未经出库取消_并告警迟迟未已取():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 2)
    scheduler.arrive(1, 1)
    scheduler.see("甲", None)
    scheduler.advance(2.9)

    assert not has_alert(scheduler, "迟迟未已取")
    assert scheduler.cell_of("甲") == 1

    scheduler.advance(0.1)

    assert scheduler.cell_of("甲") == 1
    assert scheduler.name_of("甲") is None
    assert not has_alert(scheduler, "未经出库")
    assert has_alert(scheduler, "迟迟未已取", number="甲")
    assert scheduler.task(task.task_id).status == "执行中"
    assert scheduler.vehicle(1).may_drive is False


def test_三秒内已取就不再告警迟迟未已取():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.transfer("甲", 2)
    scheduler.arrive(1, 1)
    scheduler.advance(2.9)
    scheduler.see("甲", Bed(1))
    scheduler.advance(5)

    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.vehicle(1).may_drive is True
    assert not has_alert(scheduler, "迟迟未已取")
    assert not has_alert(scheduler, "未经出库")


def test_车还没到货已换格_仍去冻结的取货货位_核对失败只结束这一条():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 3)
    moving = scheduler.transfer("甲", 4)
    other = scheduler.transfer("乙", 6)
    scheduler.see("甲", 8)

    assert scheduler.vehicle(1).target == 1
    assert scheduler.task(moving.task_id).pickup == 1
    assert scheduler.cell_of("甲") == 8

    scheduler.arrive(1, 1)

    assert scheduler.task(moving.task_id).status == "已结束"
    assert scheduler.task(moving.task_id).end_reason == "核对不符"
    assert has_alert(scheduler, "核对不符", number="甲")
    assert scheduler.vehicle(1).task_id is None
    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.cell_of("甲") == 8
    assert scheduler.cell_free(1)
    assert scheduler.vehicle(2).may_drive is True
    assert scheduler.vehicle(2).target == 3

    run_until_drop(scheduler, 2, "乙", 3, 6)

    assert scheduler.task(other.task_id).status == "已结束"
    assert scheduler.task(other.task_id).end_reason == "已到位"
    assert scheduler.task(moving.task_id).status == "已结束"


def test_已取前放进别的货位不算已取_登记改过去_车留在取货点_任务继续():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 9)
    scheduler.arrive(1, 1)
    scheduler.see("甲", 6)

    assert scheduler.cell_of("甲") == 6
    assert scheduler.vehicle_of("甲") is None
    assert has_alert(scheduler, "放错格", number="甲", cell=6)
    assert alert(scheduler, "放错格", "甲").awaits_confirmation is True
    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.task(task.task_id).status == "执行中"
    assert scheduler.task(task.task_id).pickup == 1

    scheduler.see("甲", Bed(1))

    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 9
    assert scheduler.task(task.task_id).route == (1, 2, 3, 6, 9)


def test_已取后放错格结束任务_警报留到仓管员确认_确认不搬货():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 4)
    scheduler.arrive(1, 1)
    scheduler.see("甲", Bed(1))
    scheduler.see("甲", 8)

    assert scheduler.task(task.task_id).status == "已结束"
    assert scheduler.task(task.task_id).end_reason == "放错格"
    assert scheduler.cell_of("甲") == 8
    assert scheduler.vehicle_of("甲") is None
    assert scheduler.cell_free(8) is False
    assert scheduler.cell_free(4) is True
    assert scheduler.vehicle(1).task_id is None
    wrong = alert(scheduler, "放错格", "甲")
    assert wrong.awaits_confirmation is True
    assert wrong.cell == 8

    scheduler.confirm_wrong_cell("甲")

    assert not has_alert(scheduler, "放错格")
    assert scheduler.cell_of("甲") == 8
    again = scheduler.transfer("甲", 9)
    assert again.accepted
    assert scheduler.task(again.task_id).pickup == 8


def test_移库在报到放货货位时结束_已放之前货物仍在车上且该格不空闲():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 7)
    task = scheduler.transfer("甲", 4)
    run_until_loaded(scheduler, 1, "甲", 1)

    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.cell_free(4) is False

    scheduler.arrive(1, 4)

    assert scheduler.task(task.task_id).status == "已结束"
    assert scheduler.task(task.task_id).end_reason == "已到位"
    assert scheduler.vehicle(1).task_id is None
    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.cell_of("甲") is None
    assert scheduler.cell_free(4) is False
    assert not scheduler.transfer("乙", 4).accepted

    scheduler.see("甲", 4)

    assert scheduler.cell_of("甲") == 4
    assert scheduler.vehicle_of("甲") is None
    assert scheduler.cell_free(4) is False


def test_车已空出来但仍未已放时_这辆车可以接下一条_放货货位仍不空闲():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 3)
    scheduler.transfer("甲", 4)
    run_until_drop(scheduler, 1, "甲", 1, 4)

    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.vehicle(1).task_id is None
    nxt = scheduler.transfer("乙", 6)
    assert nxt.accepted
    assert scheduler.task(nxt.task_id).vehicle == 1
    assert not scheduler.cell_free(4)


def test_入库单上的名称要等场外核对通过才保存_失败则保持原名称():
    scheduler = Scheduler()
    scheduler.bind_name("N-1", "旧名")
    task = scheduler.inbound("N-1", "新名", 5)

    assert task.accepted
    assert scheduler.name_of("N-1") == "旧名"
    assert scheduler.vehicle(1).target == OUTSIDE
    assert scheduler.task(task.task_id).route == (OUTSIDE, 2, 5)

    scheduler.arrive(1, OUTSIDE)
    assert scheduler.name_of("N-1") == "旧名"
    assert scheduler.vehicle(1).may_drive is False

    scheduler.see("N-1", OUTSIDE)
    assert scheduler.name_of("N-1") == "新名"
    assert scheduler.cell_of("N-1") is None

    scheduler.advance(3)
    assert has_alert(scheduler, "迟迟未已取", number="N-1")
    assert scheduler.task(task.task_id).status == "执行中"
    scheduler.see("N-1", Bed(1))
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 5


def test_入库核对失败结束任务_放货货位释放_新编号不留下名称():
    failed = Scheduler()
    failed.bind_name("N-1", "旧名")
    task = failed.inbound("N-1", "新名", 5)
    failed.arrive(1, OUTSIDE)
    failed.see("别的货", OUTSIDE)
    failed.advance(3)

    assert failed.task(task.task_id).status == "已结束"
    assert failed.task(task.task_id).end_reason == "核对不符"
    assert failed.name_of("N-1") == "旧名"
    assert failed.cell_free(5)
    assert failed.outside_free()
    assert failed.vehicle(1).task_id is None
    assert has_alert(failed, "核对不符", number="N-1")

    fresh = Scheduler()
    created = fresh.inbound("N-9", "打错了", 6)
    fresh.arrive(1, OUTSIDE)
    fresh.advance(3)

    assert fresh.task(created.task_id).end_reason == "核对不符"
    assert fresh.name_of("N-9") is None
    assert fresh.cell_free(6)


def test_入库已取前出现在货位按放错格_车留在场外_任务继续_名称尚未改():
    scheduler = Scheduler()
    scheduler.bind_name("N-1", "旧名")
    task = scheduler.inbound("N-1", "新名", 5)
    scheduler.see("N-1", 8)

    assert scheduler.cell_of("N-1") == 8
    assert has_alert(scheduler, "放错格", number="N-1", cell=8)
    assert not has_alert(scheduler, "未经入库", number="N-1")
    assert scheduler.name_of("N-1") == "旧名"
    assert scheduler.task(task.task_id).status == "执行中"
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == OUTSIDE

    scheduler.arrive(1, OUTSIDE)

    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.task(task.task_id).status == "执行中"
    assert scheduler.name_of("N-1") == "旧名"

    scheduler.see("N-1", OUTSIDE)
    assert scheduler.name_of("N-1") == "新名"
    assert scheduler.vehicle(1).may_drive is False

    scheduler.see("N-1", Bed(1))
    assert scheduler.vehicle(1).target == 5
    assert scheduler.vehicle_of("N-1") == 1


def test_入库报到放货货位才结束_之前该格不空闲():
    scheduler = Scheduler()
    task = scheduler.inbound("N-1", "电机", 5)
    scheduler.arrive(1, OUTSIDE)
    scheduler.see("N-1", OUTSIDE)
    scheduler.see("N-1", Bed(1))
    assert not scheduler.cell_free(5)
    assert scheduler.cell_of("N-1") is None

    scheduler.arrive(1, 5)

    assert scheduler.task(task.task_id).status == "已结束"
    assert scheduler.task(task.task_id).end_reason == "已到位"
    assert scheduler.vehicle_of("N-1") == 1
    assert not scheduler.cell_free(5)
    scheduler.see("N-1", 5)
    assert scheduler.cell_of("N-1") == 5
    assert scheduler.vehicle_of("N-1") is None


def test_出库报到场外就离开登记_名称留下_场外立刻空出来():
    scheduler = Scheduler()
    scheduler.see("N-1", 8)
    scheduler.bind_name("N-1", "箱子")
    task = scheduler.outbound("N-1")

    assert scheduler.task(task.task_id).route == (8, 5, 2, OUTSIDE)
    assert scheduler.vehicle(1).target == 8

    run_until_loaded(scheduler, 1, "N-1", 8)
    assert scheduler.vehicle(1).target == OUTSIDE
    scheduler.arrive(1, OUTSIDE)

    assert scheduler.task(task.task_id).status == "已结束"
    assert scheduler.task(task.task_id).end_reason == "已到位"
    assert scheduler.cell_of("N-1") is None
    assert scheduler.vehicle_of("N-1") is None
    assert scheduler.name_of("N-1") == "箱子"
    assert scheduler.outside_free()

    stayed = scheduler.alerts()
    scheduler.see("N-1", OUTSIDE)
    scheduler.advance(5)

    assert scheduler.cell_of("N-1") is None
    assert scheduler.alerts() == stayed
    assert scheduler.outside_free()
    assert scheduler.name_of("N-1") == "箱子"

    again = scheduler.inbound("N-1", "箱子", 4)
    assert again.accepted
    assert scheduler.name_of("N-1") == "箱子"


def test_未结束的入库或出库独占场外_第二条直接拒绝_移库仍可下发():
    scheduler = Scheduler()
    first = scheduler.inbound("N-1", "电机", 5)
    second = scheduler.inbound("N-2", "泵", 6)
    outgoing = scheduler.outbound("没有")

    assert first.accepted
    assert not second.accepted
    assert second.reason == "场外已被占用"
    assert [task.kind for task in scheduler.tasks()] == ["入库"]
    assert not outgoing.accepted

    scheduler.see("甲", 1)
    moving = scheduler.transfer("甲", 4)
    assert moving.accepted
    assert scheduler.task(moving.task_id).vehicle == 2
    assert scheduler.outside_free() is False


def test_场外被待派占住时第二条进出库拒绝_不进入待派():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货", 7)
    pending = scheduler.outbound("货")
    assert pending.accepted
    assert scheduler.task(pending.task_id).status == "待派"
    assert scheduler.outside_free() is False

    refused = scheduler.inbound("新", "名", 9)
    assert not refused.accepted
    assert refused.reason == "场外已被占用"
    assert [task.status for task in scheduler.tasks()].count("待派") == 1

    scheduler.see("旁", 8)
    moving = scheduler.transfer("旁", 9)
    assert moving.accepted
    assert scheduler.task(moving.task_id).status == "待派"


def test_待派从收下起占住货物和放货货位_取货货位跟着登记走_空车时先下发的先冻结():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货甲", 8)
    scheduler.see("货乙", 7)
    first = scheduler.transfer("货甲", 9)
    second = scheduler.transfer("货乙", 2)

    assert scheduler.task(first.task_id).status == "待派"
    assert scheduler.task(first.task_id).pickup == 8
    assert not scheduler.cell_free(8)
    assert not scheduler.cell_free(9)
    assert not scheduler.transfer("货甲", 5).accepted
    assert scheduler.transfer("货甲", 5).reason == "该货物已有未结束任务"
    assert not scheduler.transfer("货乙", 9).accepted
    assert not scheduler.transfer("货乙", 8).accepted

    scheduler.see("货甲", 5)
    assert scheduler.task(first.task_id).pickup == 5
    assert scheduler.task(first.task_id).route == (5, 6, 9)
    assert scheduler.cell_free(8)
    assert not scheduler.cell_free(5)

    run_until_drop(scheduler, 2, "占-2", 3, 6)

    assert scheduler.task(first.task_id).vehicle == 2
    assert scheduler.task(first.task_id).status == "执行中"
    assert scheduler.task(first.task_id).pickup == 5
    assert scheduler.vehicle(2).target == 5
    assert scheduler.task(second.task_id).status == "待派"

    scheduler.see("货甲", 2)
    assert scheduler.vehicle(2).target == 5
    assert scheduler.task(first.task_id).pickup == 5
    scheduler.arrive(2, 5)
    assert scheduler.task(first.task_id).status == "已结束"
    assert scheduler.task(first.task_id).end_reason == "核对不符"
    assert scheduler.cell_of("货甲") == 2


def test_刚空出来的是车2时待派交给车2():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货甲", 8)
    pending = scheduler.transfer("货甲", 9)
    run_until_drop(scheduler, 2, "占-2", 3, 6)

    assert scheduler.task(pending.task_id).vehicle == 2
    assert scheduler.vehicle(1).task_id is not None


def test_一条任务的取货货位不能当另一条的放货货位_待派也算():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货甲", 8)
    scheduler.transfer("货甲", 9)
    scheduler.see("旁", 7)

    refused = scheduler.transfer("旁", 8)
    assert not refused.accepted
    assert refused.reason == "放货货位不是空闲"

    scheduler.see("占-3", 5)
    assert not scheduler.transfer("占-3", 1).accepted
    assert not scheduler.transfer("占-3", 4).accepted


def test_路线不相交的两辆车可以同时开():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 3)
    left = scheduler.transfer("甲", 4)
    right = scheduler.transfer("乙", 6)
    scheduler.arrive(1, 1)
    scheduler.see("甲", Bed(1))
    scheduler.arrive(2, 3)
    scheduler.see("乙", Bed(2))

    assert scheduler.task(left.task_id).status == "执行中"
    assert scheduler.task(right.task_id).status == "执行中"
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 4
    assert scheduler.vehicle(2).may_drive is True
    assert scheduler.vehicle(2).target == 6
    assert scheduler.task(left.task_id).route == (1, 4)
    assert scheduler.task(right.task_id).route == (3, 6)


def test_后完成已取且路线交叉的车等路_直到另一条任务结束_路线不改():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 3)
    first = scheduler.transfer("甲", 9)
    second = scheduler.transfer("乙", 7)
    assert scheduler.task(first.task_id).route == (1, 2, 3, 6, 9)
    assert scheduler.task(second.task_id).route == (3, 2, 1, 4, 7)

    scheduler.arrive(1, 1)
    scheduler.see("甲", Bed(1))
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 9

    scheduler.arrive(2, 3)
    scheduler.see("乙", Bed(2))

    assert scheduler.task(second.task_id).status == "等路"
    assert scheduler.vehicle(2).may_drive is False
    assert scheduler.task(second.task_id).route == (3, 2, 1, 4, 7)
    scheduler.arrive(2, 7)
    assert scheduler.task(second.task_id).status == "等路"

    scheduler.arrive(1, 9)
    assert scheduler.task(first.task_id).status == "已结束"
    assert scheduler.task(second.task_id).status == "执行中"
    assert scheduler.vehicle(2).may_drive is True
    assert scheduler.vehicle(2).target == 7
    assert scheduler.task(second.task_id).route == (3, 2, 1, 4, 7)


def test_先完成已取的那辆不等_后完成的才等():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.see("乙", 3)
    scheduler.transfer("甲", 9)
    later = scheduler.transfer("乙", 7)
    scheduler.arrive(2, 3)
    scheduler.see("乙", Bed(2))

    assert scheduler.task(later.task_id).status == "执行中"
    assert scheduler.vehicle(2).may_drive is True

    scheduler.arrive(1, 1)
    scheduler.see("甲", Bed(1))
    assert scheduler.task(scheduler.vehicle(1).task_id).status == "等路"
    assert scheduler.vehicle(1).may_drive is False


def test_入库和移库在2号交叉时后已取的车等路():
    scheduler = Scheduler()
    scheduler.see("甲", 4)
    inbound = scheduler.inbound("N-1", "电机", 5)
    moving = scheduler.transfer("甲", 6)
    assert scheduler.task(inbound.task_id).route == (OUTSIDE, 2, 5)
    assert scheduler.task(moving.task_id).route == (4, 5, 6)

    scheduler.arrive(1, OUTSIDE)
    scheduler.see("N-1", OUTSIDE)
    scheduler.see("N-1", Bed(1))
    scheduler.arrive(2, 4)
    scheduler.see("甲", Bed(2))

    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.task(moving.task_id).status == "等路"
    assert scheduler.vehicle(2).may_drive is False


def test_断云时调度台离线_执行中的任务继续_待派不发车_新任务拒绝_恢复后告警和待派出现():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货甲", 8)
    pending = scheduler.transfer("货甲", 9)
    scheduler.disconnect()

    assert scheduler.console_status() == "离线"
    assert scheduler.console_alerts() == []
    assert not scheduler.transfer("货甲", 2).accepted
    scheduler.see("旁", 7)
    assert not scheduler.outbound("旁").accepted
    assert scheduler.outbound("旁").reason == "断云"

    scheduler.see("占-1", 2)
    scheduler.arrive(1, 1)

    assert scheduler.task(scheduler.tasks()[0].id).status == "已结束"
    assert scheduler.task(scheduler.tasks()[0].id).end_reason == "核对不符"
    assert scheduler.vehicle(1).task_id is None
    assert scheduler.vehicle(1).may_drive is False
    assert scheduler.task(pending.task_id).status == "待派"
    assert has_alert(scheduler, "核对不符", number="占-1")
    assert scheduler.console_alerts() == []

    scheduler.reconnect()

    assert scheduler.console_status() == "在线"
    assert has_alert(scheduler, "核对不符", number="占-1")
    assert scheduler.console_alerts() == scheduler.alerts()
    assert scheduler.task(pending.task_id).status == "执行中"
    assert scheduler.task(pending.task_id).vehicle == 1
    assert scheduler.vehicle(1).may_drive is True
    assert scheduler.vehicle(1).target == 8


def test_断云期间已经装上车的任务仍开到目的地并报到():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 4)
    scheduler.arrive(1, 1)
    scheduler.see("甲", Bed(1))
    scheduler.disconnect()

    assert scheduler.vehicle(1).may_drive is True
    scheduler.arrive(1, 4)

    assert scheduler.task(task.task_id).status == "已结束"
    assert scheduler.task(task.task_id).end_reason == "已到位"
    assert scheduler.vehicle_of("甲") == 1
    assert scheduler.console_status() == "离线"
    assert not scheduler.cell_free(4)


def test_云恢复后两辆车都空闲时待派仍按先下发的先走():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货甲", 8)
    scheduler.see("货乙", 7)
    first = scheduler.transfer("货甲", 9)
    second = scheduler.transfer("货乙", 2)
    scheduler.disconnect()
    run_until_drop(scheduler, 1, "占-1", 1, 4)
    run_until_drop(scheduler, 2, "占-2", 3, 6)

    assert scheduler.task(first.task_id).status == "待派"
    assert scheduler.task(second.task_id).status == "待派"
    assert scheduler.vehicle(1).task_id is None
    assert scheduler.vehicle(2).task_id is None

    scheduler.reconnect()

    assert scheduler.task(first.task_id).vehicle == 1
    assert scheduler.task(first.task_id).status == "执行中"
    assert scheduler.task(first.task_id).pickup == 8
    assert scheduler.task(second.task_id).vehicle == 2
    assert scheduler.task(second.task_id).status == "执行中"


def test_待派的货物连续三秒读不到就离开登记并放开占住的格子():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货甲", 8)
    scheduler.bind_name("货甲", "甲")
    pending = scheduler.transfer("货甲", 9)
    scheduler.see("货甲", None)
    scheduler.advance(3)

    assert scheduler.cell_of("货甲") is None
    assert scheduler.name_of("货甲") == "甲"
    assert scheduler.cell_free(8)
    assert scheduler.cell_free(9)
    assert scheduler.task(pending.task_id).status == "已结束"
    assert scheduler.task(pending.task_id).end_reason == "未经出库"
    assert has_alert(scheduler, "未经出库", number="货甲", cell=8)
    assert scheduler.vehicle(1).task_id is not None
    assert scheduler.vehicle(2).task_id is not None


def test_出库待派也占住场外_取货货位跟着当前登记():
    scheduler = Scheduler()
    occupy_both(scheduler)
    scheduler.see("货", 7)
    pending = scheduler.outbound("货")
    assert not scheduler.outside_free()
    scheduler.see("货", 5)

    assert scheduler.task(pending.task_id).pickup == 5
    assert scheduler.cell_free(7)
    assert not scheduler.cell_free(5)
    assert not scheduler.inbound("新", "名", 9).accepted


def test_已放之后登记在指定货位_不再算在车上():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    scheduler.transfer("甲", 4)
    run_until_drop(scheduler, 1, "甲", 1, 4)
    scheduler.see("甲", 4)

    assert scheduler.cell_of("甲") == 4
    assert scheduler.vehicle_of("甲") is None


def test_已取后任务已结束但还没放下_又被读到别的格子_放错格留着():
    scheduler = Scheduler()
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 4)
    run_until_drop(scheduler, 1, "甲", 1, 4)
    scheduler.see("甲", 9)

    assert scheduler.task(task.task_id).status == "已结束"
    assert scheduler.cell_of("甲") == 9
    assert scheduler.cell_free(4)
    assert not scheduler.cell_free(9)
    assert has_alert(scheduler, "放错格", number="甲", cell=9)
    scheduler.confirm_wrong_cell("甲")
    assert scheduler.cell_of("甲") == 9
    assert not has_alert(scheduler, "放错格")


def test_等已取时手挡住超过三秒_任务不结束():
    scheduler = Scheduler()
    scheduler.bind_name("甲", "零件")
    scheduler.see("甲", 1)
    task = scheduler.transfer("甲", 2)
    scheduler.arrive(1, 1)
    scheduler.see("甲", None)
    scheduler.advance(5)

    assert scheduler.task(task.task_id).status == "执行中"
    assert scheduler.cell_of("甲") == 1
    assert scheduler.name_of("甲") == "零件"
    assert not has_alert(scheduler, "未经出库")
    assert scheduler.vehicle(1).may_drive is False


def occupy_both(scheduler: Scheduler) -> None:
    scheduler.see("占-1", 1)
    scheduler.see("占-2", 3)
    scheduler.transfer("占-1", 4)
    scheduler.transfer("占-2", 6)


def run_until_loaded(scheduler: Scheduler, vehicle: int, number: str, pickup: int | str) -> None:
    assert scheduler.vehicle(vehicle).may_drive is True
    assert scheduler.vehicle(vehicle).target == pickup
    scheduler.arrive(vehicle, pickup)
    assert scheduler.vehicle(vehicle).may_drive is False
    scheduler.see(number, Bed(vehicle))


def run_until_drop(
    scheduler: Scheduler,
    vehicle: int,
    number: str,
    pickup: int | str,
    drop: int | str,
) -> None:
    run_until_loaded(scheduler, vehicle, number, pickup)
    assert scheduler.vehicle(vehicle).may_drive is True
    assert scheduler.vehicle(vehicle).target == drop
    scheduler.arrive(vehicle, drop)


def has_alert(scheduler: Scheduler, kind: str, number: str | None = None, cell: int | None = None) -> bool:
    return alert(scheduler, kind, number, cell) is not None


def alert(scheduler: Scheduler, kind: str, number: str | None = None, cell: int | None = None):
    for item in scheduler.alerts():
        if item.kind != kind:
            continue
        if number is not None and item.number != number:
            continue
        if cell is not None and item.cell != cell:
            continue
        return item
    return None
