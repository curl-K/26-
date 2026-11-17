package edu.whpu.reagent.service;

import edu.whpu.reagent.domain.CabinetSession;

import java.time.LocalDateTime;

public final class Sessions {

    private Sessions() {
    }

    public static boolean waitingExpired(CabinetSession session, LocalDateTime now) {
        return session.getExpiresAt() != null && !now.isBefore(session.getExpiresAt());
    }

    public static boolean openExpired(CabinetSession session, LocalDateTime now) {
        return session.getOpenedAt() != null && !now.isBefore(session.getOpenedAt().plusMinutes(5));
    }

    public static void close(CabinetSession session, LocalDateTime now, String reason) {
        session.setState("closed");
        session.setClosedAt(now);
        session.setCloseReason(reason);
    }

    public static void blankChipState(CabinetSession session) {
        session.setStreak(0);
        session.setPresentUids("");
        session.setRemovedUids("");
        session.setIgnoredUids("");
        session.setSuppressed(false);
        session.setDualAlarm(false);
    }
}
