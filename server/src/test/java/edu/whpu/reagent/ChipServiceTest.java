package edu.whpu.reagent;

import edu.whpu.reagent.service.CatalogService;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ChipServiceTest {

    @Test
    void twoReadsBindThePendingBottle() {
        Lab lab = new Lab();
        assertEquals("ok", lab.catalog.register("乙醇", "低", 1).result());
        assertEquals("pending_exists", lab.catalog.register("另一瓶", "中", 1).result());
        lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        assertEquals("seen", lab.chip.observe(lab.seq(), 1, "E1").result());
        assertEquals("待绑定", only(lab).status());
        assertEquals("recorded", lab.chip.observe(lab.seq(), 1, "E1").result());
        CatalogService.ReagentView row = only(lab);
        assertEquals("在柜", row.status());
        assertEquals("E1", row.chipUid());
        assertEquals(List.of("陈"), row.handlers());
    }

    @Test
    void aSingleReadIsNotAReturn() {
        Lab lab = new Lab();
        lab.catalog.register("乙醇", "低", 1);
        lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        lab.chip.observe(lab.seq(), 1, "E1");
        assertEquals("closed", lab.chip.end(lab.seq(), 1, "button").result());
        assertEquals("待绑定", only(lab).status());
        assertNull(only(lab).chipUid());
        assertTrue(only(lab).handlers().isEmpty());
    }

    @Test
    void twoMissesMarkTheBottleTaken() {
        Lab lab = new Lab();
        bind(lab, 1, "乙醇", "低", "chen", null, "E1");
        lab.chip.end(lab.seq(), 1, "button");
        lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        assertEquals("seen", lab.chip.observe(lab.seq(), 1, "E1").result());
        assertEquals("ignored", lab.chip.observe(lab.seq(), 1, "E1").result());
        assertEquals("seen", lab.chip.observe(lab.seq(), 1, "").result());
        assertEquals("recorded", lab.chip.observe(lab.seq(), 1, null).result());
        CatalogService.ReagentView row = only(lab);
        assertEquals("已取出", row.status());
        assertEquals(List.of("陈"), row.handlers());
    }

    @Test
    void unknownChipRaisesAnAlarmAndDoesNotAddARow() {
        Lab lab = new Lab();
        lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        lab.chip.observe(lab.seq(), 1, "XX");
        assertEquals("unbound_chip", lab.chip.observe(lab.seq(), 1, "XX").result());
        assertTrue(lab.catalog.list().isEmpty());
        assertEquals("unbound_chip", lab.catalog.alarms().get(0).code());
    }

    @Test
    void twoChipsInOneSlotAreNotBooked() {
        Lab lab = new Lab();
        lab.catalog.register("乙醇", "低", 1);
        lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        lab.chip.observe(lab.seq(), 1, "A");
        lab.chip.observe(lab.seq(), 1, "A");
        assertEquals("seen", lab.chip.observe(lab.seq(), 1, "B").result());
        assertEquals("dual_chip", lab.chip.observe(lab.seq(), 1, "B").result());
        CatalogService.ReagentView row = only(lab);
        assertEquals("待绑定", row.status());
        assertNull(row.chipUid());
        assertTrue(row.handlers().isEmpty());
        assertEquals("dual_chip", lab.catalog.alarms().get(0).code());
    }

    @Test
    void aBottleReadInTheWrongSlotIsNotMoved() {
        Lab lab = new Lab();
        bind(lab, 1, "乙醇", "低", "chen", null, "E1");
        lab.chip.end(lab.seq(), 1, "button");
        lab.confirm.confirm(lab.seq(), 2, "chen", "chen123");
        lab.confirm.confirm(lab.seq(), 2, "li", "li123");
        lab.chip.observe(lab.seq(), 2, "E1");
        assertEquals("level_cell_mismatch", lab.chip.observe(lab.seq(), 2, "E1").result());
        CatalogService.ReagentView row = only(lab);
        assertEquals(1, row.slot());
        assertEquals("在柜", row.status());
    }

    @Test
    void slotTwoRecordsBothHandlers() {
        Lab lab = new Lab();
        lab.catalog.register("硫酸", "高", 2);
        lab.confirm.confirm(lab.seq(), 2, "chen", "chen123");
        lab.confirm.confirm(lab.seq(), 2, "li", "li123");
        lab.chip.observe(lab.seq(), 2, "H1");
        lab.chip.observe(lab.seq(), 2, "H1");
        assertEquals(List.of("陈", "李"), only(lab).handlers());
        assertEquals("在柜", only(lab).status());
    }

    @Test
    void managerCanDeleteAReagentFromTheList() {
        Lab lab = new Lab();
        lab.catalog.register("乙醇", "低", 1);
        long id = lab.catalog.list().get(0).id();
        lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        lab.chip.observe(lab.seq(), 1, "E1");
        lab.chip.observe(lab.seq(), 1, "E1");
        assertEquals("ok", lab.catalog.delete(id).result());
        assertTrue(lab.catalog.list().isEmpty());
        assertEquals("not_found", lab.catalog.delete(id).result());
    }

    @Test
    void highLevelCannotBeRegisteredInSlotOne() {
        Lab lab = new Lab();
        assertEquals("level_cell_mismatch", lab.catalog.register("硫酸", "高", 1).result());
        assertTrue(lab.catalog.list().isEmpty());
    }

    private static void bind(Lab lab, int slot, String name, String level, String first, String second, String uid) {
        lab.catalog.register(name, level, slot);
        lab.confirm.confirm(lab.seq(), slot, first, first + "123");
        if (second != null) {
            lab.confirm.confirm(lab.seq(), slot, second, second + "123");
        }
        lab.chip.observe(lab.seq(), slot, uid);
        lab.chip.observe(lab.seq(), slot, uid);
    }

    private static CatalogService.ReagentView only(Lab lab) {
        return lab.catalog.list().get(0);
    }
}
