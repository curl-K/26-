package edu.whpu.reagent;

import edu.whpu.reagent.domain.AccessRecord;
import edu.whpu.reagent.domain.Account;
import edu.whpu.reagent.domain.Alarm;
import edu.whpu.reagent.domain.CabinetSession;
import edu.whpu.reagent.domain.Reagent;
import edu.whpu.reagent.domain.Sample;
import edu.whpu.reagent.persistence.CabinetRepository;
import edu.whpu.reagent.persistence.ReagentListRow;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public class MemoryCabinetRepository implements CabinetRepository {

    private final Map<Long, Account> accounts = new LinkedHashMap<>();
    private final Map<Long, Reagent> reagents = new LinkedHashMap<>();
    private final Map<Long, CabinetSession> sessions = new LinkedHashMap<>();
    private final Map<Long, AccessRecord> access = new LinkedHashMap<>();
    private final Map<Long, Alarm> alarms = new LinkedHashMap<>();
    private final Map<Long, Sample> samples = new LinkedHashMap<>();
    private long nextId = 1;
    private int lastSeq;
    private LocalDateTime heartbeat;

    @Override
    public Optional<Account> findAccountByUsername(String username) {
        return accounts.values().stream().filter(account -> account.getUsername().equals(username)).findFirst();
    }

    @Override
    public void insertAccount(Account account) {
        account.setId(nextId++);
        accounts.put(account.getId(), account);
    }

    @Override
    public void updateAccount(Account account) {
        accounts.put(account.getId(), account);
    }

    @Override
    public Optional<Account> findAccountById(long id) {
        return Optional.ofNullable(accounts.get(id));
    }

    @Override
    public List<ReagentListRow> listReagentRows() {
        List<Reagent> rows = new ArrayList<>(reagents.values());
        rows.sort(Comparator.comparingInt(Reagent::getSlotNo).thenComparing(Reagent::getId));
        List<ReagentListRow> result = new ArrayList<>();
        for (Reagent reagent : rows) {
            ReagentListRow row = new ReagentListRow();
            row.setId(reagent.getId());
            row.setName(reagent.getName());
            row.setLevel(reagent.getLevel());
            row.setSlotNo(reagent.getSlotNo());
            row.setStatus(reagent.getStatus());
            row.setChipUid(reagent.getChipUid());
            AccessRecord latest = null;
            for (AccessRecord record : access.values()) {
                if (!record.getReagentId().equals(reagent.getId())) {
                    continue;
                }
                if (latest == null || record.getOccurredAt().isAfter(latest.getOccurredAt()) || record.getId() > latest.getId()) {
                    latest = record;
                }
            }
            if (latest != null) {
                row.setHandler1(latest.getHandler1());
                row.setHandler2(latest.getHandler2());
                row.setOccurredAt(latest.getOccurredAt());
            }
            result.add(row);
        }
        return result;
    }

    @Override
    public Optional<Reagent> findReagent(long id) {
        return Optional.ofNullable(reagents.get(id));
    }

    @Override
    public Optional<Reagent> findPendingBind(int slot) {
        return reagents.values().stream()
                .filter(reagent -> reagent.getSlotNo() == slot && "pending".equals(reagent.getStatus()))
                .min(Comparator.comparing(Reagent::getId));
    }

    @Override
    public Optional<Reagent> findReagentByChip(String uid) {
        if (uid == null || uid.isBlank()) {
            return Optional.empty();
        }
        return reagents.values().stream().filter(reagent -> uid.equals(reagent.getChipUid())).findFirst();
    }

    @Override
    public void insertReagent(Reagent reagent) {
        reagent.setId(nextId++);
        reagents.put(reagent.getId(), reagent);
    }

    @Override
    public void updateReagent(Reagent reagent) {
        reagents.put(reagent.getId(), reagent);
    }

    @Override
    public Optional<CabinetSession> findActiveSession(int slot) {
        return sessions.values().stream()
                .filter(session -> session.getSlotNo() == slot && ("waiting".equals(session.getState()) || "open".equals(session.getState())))
                .max(Comparator.comparing(CabinetSession::getId));
    }

    @Override
    public void insertSession(CabinetSession session) {
        session.setId(nextId++);
        sessions.put(session.getId(), session);
    }

    @Override
    public void updateSession(CabinetSession session) {
        sessions.put(session.getId(), session);
    }

    @Override
    public void insertAccess(AccessRecord record) {
        record.setId(nextId++);
        access.put(record.getId(), record);
    }

    @Override
    public List<AccessRecord> listAccessBySession(long sessionId) {
        List<AccessRecord> rows = new ArrayList<>();
        for (AccessRecord record : access.values()) {
            if (record.getSessionId() == sessionId) {
                rows.add(record);
            }
        }
        rows.sort(Comparator.comparing(AccessRecord::getId));
        return rows;
    }

    @Override
    public void deleteAccess(long id) {
        access.remove(id);
    }

    @Override
    public void insertAlarm(Alarm alarm) {
        alarm.setId(nextId++);
        alarms.put(alarm.getId(), alarm);
    }

    @Override
    public List<Alarm> listAlarms() {
        List<Alarm> rows = new ArrayList<>(alarms.values());
        rows.sort(Comparator.comparing(Alarm::isAcknowledged).thenComparing(Alarm::getId, Comparator.reverseOrder()));
        if (rows.size() > 50) {
            return rows.subList(0, 50);
        }
        return rows;
    }

    @Override
    public int acknowledge(long id, long accountId, LocalDateTime at) {
        Alarm alarm = alarms.get(id);
        if (alarm == null || alarm.isAcknowledged()) {
            return 0;
        }
        alarm.setAcknowledged(true);
        alarm.setAcknowledgedBy(accountId);
        alarm.setAcknowledgedAt(at);
        return 1;
    }

    @Override
    public void insertSample(Sample sample) {
        sample.setId(nextId++);
        samples.put(sample.getId(), sample);
    }

    @Override
    public void deleteSamplesBefore(LocalDateTime cutoff) {
        samples.values().removeIf(sample -> sample.getSampledAt().isBefore(cutoff));
    }

    @Override
    public List<Sample> latestSamples(int limit) {
        List<Sample> rows = new ArrayList<>(samples.values());
        rows.sort(Comparator.comparing(Sample::getSampledAt).reversed().thenComparing(Sample::getId, Comparator.reverseOrder()));
        if (rows.size() > limit) {
            return rows.subList(0, limit);
        }
        return rows;
    }

    @Override
    public int lastSeq() {
        return lastSeq;
    }

    @Override
    public void saveSeq(int seq) {
        lastSeq = seq;
    }

    @Override
    public void touchHeartbeat(LocalDateTime at) {
        heartbeat = at;
    }

    @Override
    public Optional<LocalDateTime> lastHeartbeat() {
        return Optional.ofNullable(heartbeat);
    }
}
