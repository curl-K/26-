package edu.whpu.reagent;

import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.service.BusinessException;
import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ConfirmServiceTest {

    @Test
    void correctPasswordOpensSlotOneWithoutAChip() {
        Lab lab = new Lab();
        Outcome outcome = lab.confirm.confirm(lab.seq(), 1, "chen", "chen123");
        assertEquals("allow", outcome.result());
        assertTrue(lab.catalog.list().isEmpty());
        assertEquals("open", lab.repo.findActiveSession(1).orElseThrow().getState());
    }

    @Test
    void wrongPasswordLocksOnTheThirdTry() {
        Lab lab = new Lab();
        assertEquals("bad_password", lab.confirm.confirm(lab.seq(), 1, "chen", "no").result());
        assertEquals("bad_password", lab.confirm.confirm(lab.seq(), 1, "chen", "no").result());
        assertEquals("locked", lab.confirm.confirm(lab.seq(), 1, "chen", "no").result());
        assertEquals("locked", lab.confirm.confirm(lab.seq(), 1, "chen", "chen123").result());
        lab.clock.advance(Duration.ofSeconds(60));
        assertEquals("allow", lab.confirm.confirm(lab.seq(), 1, "chen", "chen123").result());
    }

    @Test
    void slotTwoNeedsASecondDifferentAccount() {
        Lab lab = new Lab();
        assertEquals("need_second", lab.confirm.confirm(lab.seq(), 2, "chen", "chen123").result());
        assertTrue(lab.catalog.list().isEmpty());
        assertEquals("waiting", lab.repo.findActiveSession(2).orElseThrow().getState());

        assertEquals("same_account", lab.confirm.confirm(lab.seq(), 2, "chen", "chen123").result());
        assertTrue(lab.repo.findActiveSession(2).isEmpty());

        assertEquals("need_second", lab.confirm.confirm(lab.seq(), 2, "chen", "chen123").result());
        Outcome opened = lab.confirm.confirm(lab.seq(), 2, "li", "li123");
        assertEquals("allow", opened.result());
        var session = lab.repo.findActiveSession(2).orElseThrow();
        assertEquals("陈", session.getFirstName());
        assertEquals("李", session.getSecondName());
    }

    @Test
    void secondPersonAfterSixtySecondsDoesNotOpen() {
        Lab lab = new Lab();
        lab.confirm.confirm(lab.seq(), 2, "chen", "chen123");
        lab.clock.advance(Duration.ofSeconds(60));
        assertEquals("expired", lab.confirm.confirm(lab.seq(), 2, "li", "li123").result());
        assertTrue(lab.repo.findActiveSession(2).isEmpty());
    }

    @Test
    void replayedSequenceIsRejected() {
        Lab lab = new Lab();
        lab.confirm.confirm(1, 1, "chen", "chen123");
        BusinessException error = assertThrows(BusinessException.class,
                () -> lab.confirm.confirm(1, 1, "chen", "chen123"));
        assertEquals("replay", error.getResult());
        assertEquals(1, lab.repo.findActiveSession(1).stream().count());
    }

    @Test
    void managerPasswordDoesNotOpenTheCabinet() {
        Lab lab = new Lab();
        assertEquals("bad_password", lab.confirm.confirm(lab.seq(), 1, "manager", "manager123").result());
        assertTrue(lab.repo.findActiveSession(1).isEmpty());
    }
}
