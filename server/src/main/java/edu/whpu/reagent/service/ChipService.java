package edu.whpu.reagent.service;

import edu.whpu.reagent.domain.AccessRecord;
import edu.whpu.reagent.domain.Alarm;
import edu.whpu.reagent.domain.CabinetSession;
import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.domain.Reagent;
import edu.whpu.reagent.domain.Texts;
import edu.whpu.reagent.domain.Uids;
import edu.whpu.reagent.persistence.CabinetRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
public class ChipService {

    private final CabinetRepository repository;
    private final SeqGate seqGate;
    private final java.time.Clock clock;

    public ChipService(CabinetRepository repository, SeqGate seqGate, java.time.Clock clock) {
        this.repository = repository;
        this.seqGate = seqGate;
        this.clock = clock;
    }

    @Transactional
    public Outcome observe(int seq, int slot, String uidRaw) {
        if (slot != 1 && slot != 2) {
            return Outcome.of("bad_request", "格位只有第一格和第二格");
        }
        seqGate.consume(seq);
        LocalDateTime now = LocalDateTime.now(clock);
        CabinetSession session = repository.findActiveSession(slot).orElse(null);
        if (session == null || !"open".equals(session.getState())) {
            return Outcome.of("no_session", "这一格没有开着的会话");
        }
        if (Sessions.openExpired(session, now)) {
            Sessions.close(session, now, "timeout");
            repository.updateSession(session);
            return Outcome.of("session_timeout", "会话已满五分钟，已结束");
        }
        if (session.isSuppressed()) {
            return Outcome.of("dual_chip", "一格读到两只芯片，本次不入账");
        }
        String token = uidRaw == null ? "" : uidRaw.trim();
        String last = session.getLastReading();
        if (token.equals(last == null ? null : last)) {
            session.setStreak(session.getStreak() + 1);
        } else {
            session.setLastReading(token);
            session.setStreak(1);
        }
        Outcome outcome = token.isEmpty() ? onMiss(session, now) : onRead(session, token, now);
        repository.updateSession(session);
        return outcome;
    }

    @Transactional
    public Outcome end(int seq, int slot, String reason) {
        if (slot != 1 && slot != 2) {
            return Outcome.of("bad_request", "格位只有第一格和第二格");
        }
        seqGate.consume(seq);
        CabinetSession session = repository.findActiveSession(slot).orElse(null);
        if (session == null) {
            return Outcome.of("no_session", "这一格没有开着的会话");
        }
        String previous = session.getState();
        Sessions.close(session, LocalDateTime.now(clock), normalizeReason(reason));
        repository.updateSession(session);
        if ("waiting".equals(previous)) {
            return Outcome.of("cancelled", "已取消，门不开");
        }
        return Outcome.of("closed", "会话已结束");
    }

    private Outcome onMiss(CabinetSession session, LocalDateTime now) {
        if (session.getStreak() < 2) {
            return Outcome.of("seen", "这一次没读到");
        }
        List<String> present = Uids.split(session.getPresentUids());
        List<String> removed = Uids.split(session.getRemovedUids());
        boolean recorded = false;
        for (String uid : present) {
            if (removed.contains(uid)) {
                continue;
            }
            Reagent reagent = repository.findReagentByChip(uid).orElse(null);
            if (reagent == null || reagent.getSlotNo() != session.getSlotNo() || !"in_cabinet".equals(reagent.getStatus())) {
                removed.add(uid);
                continue;
            }
            reagent.setStatus("taken_out");
            reagent.setUpdatedAt(now);
            repository.updateReagent(reagent);
            repository.insertAccess(access(session, reagent, uid, "take", now));
            removed.add(uid);
            recorded = true;
        }
        session.setRemovedUids(Uids.join(removed));
        if (recorded) {
            return Outcome.of("recorded", "已记为取出");
        }
        return Outcome.of("ignored", "清单不变");
    }

    private Outcome onRead(CabinetSession session, String uid, LocalDateTime now) {
        if (session.getStreak() < 2) {
            return Outcome.of("seen", "已读到一次，请再放稳一次");
        }
        if (Uids.contains(session.getIgnoredUids(), uid) || Uids.contains(session.getPresentUids(), uid)) {
            return Outcome.of("ignored", "清单不变");
        }
        List<String> present = Uids.split(session.getPresentUids());
        if (!present.isEmpty()) {
            declareDual(session, now);
            return Outcome.of("dual_chip", "一格读到两只芯片，本次不入账");
        }
        Reagent known = repository.findReagentByChip(uid).orElse(null);
        if (known != null) {
            if (known.getSlotNo() != session.getSlotNo() || !Texts.levelMatches(known.getLevel(), session.getSlotNo())) {
                ignore(session, uid);
                alarm(session, uid, "level_cell_mismatch", "等级与格位不符", now);
                return Outcome.of("level_cell_mismatch", "等级与格位不符，拒绝写入");
            }
            present.add(uid);
            session.setPresentUids(Uids.join(present));
            if ("taken_out".equals(known.getStatus())) {
                known.setStatus("in_cabinet");
                known.setUpdatedAt(now);
                repository.updateReagent(known);
                repository.insertAccess(access(session, known, uid, "return", now));
                return Outcome.of("recorded", "已记为放回");
            }
            return Outcome.of("ignored", "这一瓶仍在柜中");
        }
        Reagent pending = repository.findPendingBind(session.getSlotNo()).orElse(null);
        if (pending == null || !Texts.levelMatches(pending.getLevel(), session.getSlotNo())) {
            ignore(session, uid);
            String code = pending == null ? "unbound_chip" : "level_cell_mismatch";
            String message = pending == null ? "芯片未登记" : "等级与格位不符";
            alarm(session, uid, code, message, now);
            return Outcome.of(code, message + "，不入账");
        }
        pending.setChipUid(uid);
        pending.setStatus("in_cabinet");
        pending.setUpdatedAt(now);
        repository.updateReagent(pending);
        present.add(uid);
        session.setPresentUids(Uids.join(present));
        repository.insertAccess(access(session, pending, uid, "bind", now));
        return Outcome.of("recorded", "已绑定并记为放回");
    }

    private void declareDual(CabinetSession session, LocalDateTime now) {
        List<AccessRecord> records = new ArrayList<>(repository.listAccessBySession(session.getId()));
        Collections.reverse(records);
        for (AccessRecord record : records) {
            Reagent reagent = repository.findReagent(record.getReagentId()).orElseThrow();
            if ("bind".equals(record.getAction())) {
                reagent.setChipUid(null);
                reagent.setStatus("pending");
            } else if ("return".equals(record.getAction())) {
                reagent.setStatus("taken_out");
            } else if ("take".equals(record.getAction())) {
                reagent.setStatus("in_cabinet");
            }
            reagent.setUpdatedAt(now);
            repository.updateReagent(reagent);
            repository.deleteAccess(record.getId());
        }
        session.setPresentUids("");
        session.setRemovedUids("");
        session.setSuppressed(true);
        if (!session.isDualAlarm()) {
            alarm(session, null, "dual_chip", "一格读到两只芯片，本次不入账", now);
            session.setDualAlarm(true);
        }
    }

    private void ignore(CabinetSession session, String uid) {
        List<String> ignored = Uids.split(session.getIgnoredUids());
        if (!ignored.contains(uid)) {
            ignored.add(uid);
        }
        session.setIgnoredUids(Uids.join(ignored));
    }

    private void alarm(CabinetSession session, String uid, String type, String message, LocalDateTime now) {
        Alarm alarm = new Alarm();
        alarm.setAlarmType(type);
        alarm.setChipUid(uid);
        alarm.setSlotNo(session.getSlotNo());
        alarm.setMessage(message);
        alarm.setSessionId(session.getId());
        alarm.setAcknowledged(false);
        alarm.setCreatedAt(now);
        repository.insertAlarm(alarm);
    }

    private AccessRecord access(CabinetSession session, Reagent reagent, String uid, String action, LocalDateTime now) {
        AccessRecord record = new AccessRecord();
        record.setSessionId(session.getId());
        record.setReagentId(reagent.getId());
        record.setChipUid(uid);
        record.setSlotNo(session.getSlotNo());
        record.setAction(action);
        record.setHandler1(session.getFirstName());
        record.setHandler2(session.getSecondName());
        record.setOccurredAt(now);
        return record;
    }

    private String normalizeReason(String reason) {
        if (reason == null || reason.isBlank()) {
            return "button";
        }
        return switch (reason.trim()) {
            case "timeout", "cancel", "button" -> reason.trim();
            default -> "button";
        };
    }
}
