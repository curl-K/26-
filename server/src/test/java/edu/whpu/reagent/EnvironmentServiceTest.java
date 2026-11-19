package edu.whpu.reagent;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class EnvironmentServiceTest {

    @Test
    void alarmStartsOnTheThirdConsecutiveOverrunAndDoesNotChangeTheList() {
        Lab lab = new Lab();
        lab.catalog.register("乙醇", "低", 1);
        lab.environment.record(lab.seq(), "env-1", null, 25.0, 40.0, 1500, 800);
        lab.environment.record(lab.seq(), "env-1", null, 25.0, 40.0, 1500, 800);
        assertEquals(0, envAlarms(lab));
        lab.environment.record(lab.seq(), "env-1", null, 25.0, 40.0, 1500, 800);
        assertEquals(1, envAlarms(lab));
        lab.environment.record(lab.seq(), "env-1", null, 25.0, 40.0, 1500, 800);
        assertEquals(1, envAlarms(lab));
        assertEquals("待绑定", lab.catalog.list().get(0).status());
    }

    @Test
    void theBoundaryItselfIsNotAnOverrun() {
        Lab lab = new Lab();
        lab.environment.record(lab.seq(), "env-1", null, 15.0, 20.0, 1000, 1500);
        lab.environment.record(lab.seq(), "env-1", null, 30.0, 70.0, 1000, 1500);
        lab.environment.record(lab.seq(), "env-1", null, 30.0, 70.0, 1000, 1500);
        assertEquals(0, envAlarms(lab));
    }

    @Test
    void samplesOlderThanThirtyDaysAreDropped() {
        Lab lab = new Lab();
        lab.environment.record(lab.seq(), "env-1", null, 22.0, 40.0, 10, 400);
        lab.clock.advance(Duration.ofDays(31));
        lab.environment.record(lab.seq(), "env-1", null, 22.0, 40.0, 10, 400);
        assertEquals(1, lab.repo.latestSamples(10).size());
    }

    @Test
    void heartbeatMarksTheCabinetOnline() {
        Lab lab = new Lab();
        assertFalse(lab.environment.view().online());
        lab.environment.heartbeat(lab.seq());
        assertTrue(lab.environment.view().online());
        lab.clock.advance(Duration.ofSeconds(31));
        assertFalse(lab.environment.view().online());
    }

    @Test
    void historyListsSamplesFromOldestToNewest() {
        Lab lab = new Lab();
        lab.environment.record(lab.seq(), "env-1", null, 20.0, 40.0, 10, 400);
        lab.clock.advance(Duration.ofMinutes(1));
        lab.environment.record(lab.seq(), "env-1", null, 22.0, 40.0, 30, 500);
        var history = lab.environment.view().history();
        assertEquals(2, history.size());
        assertEquals(20.0, history.get(0).temperature());
        assertEquals(22.0, history.get(1).temperature());
        assertEquals(500, history.get(1).eco2());
    }

    private static long envAlarms(Lab lab) {
        return lab.catalog.alarms().stream().filter(alarm -> "env".equals(alarm.code())).count();
    }
}
