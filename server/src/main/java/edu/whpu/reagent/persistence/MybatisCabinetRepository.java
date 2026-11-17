package edu.whpu.reagent.persistence;

import edu.whpu.reagent.domain.AccessRecord;
import edu.whpu.reagent.domain.Account;
import edu.whpu.reagent.domain.Alarm;
import edu.whpu.reagent.domain.CabinetSession;
import edu.whpu.reagent.domain.DeviceState;
import edu.whpu.reagent.domain.Reagent;
import edu.whpu.reagent.domain.Sample;
import edu.whpu.reagent.persistence.mapper.AccessMapper;
import edu.whpu.reagent.persistence.mapper.AccountMapper;
import edu.whpu.reagent.persistence.mapper.AlarmMapper;
import edu.whpu.reagent.persistence.mapper.DeviceStateMapper;
import edu.whpu.reagent.persistence.mapper.ReagentMapper;
import edu.whpu.reagent.persistence.mapper.SampleMapper;
import edu.whpu.reagent.persistence.mapper.SessionMapper;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public class MybatisCabinetRepository implements CabinetRepository {

    private final AccountMapper accounts;
    private final ReagentMapper reagents;
    private final SessionMapper sessions;
    private final AccessMapper access;
    private final AlarmMapper alarms;
    private final SampleMapper samples;
    private final DeviceStateMapper deviceState;

    public MybatisCabinetRepository(AccountMapper accounts, ReagentMapper reagents, SessionMapper sessions,
                                    AccessMapper access, AlarmMapper alarms, SampleMapper samples,
                                    DeviceStateMapper deviceState) {
        this.accounts = accounts;
        this.reagents = reagents;
        this.sessions = sessions;
        this.access = access;
        this.alarms = alarms;
        this.samples = samples;
        this.deviceState = deviceState;
    }

    @Override
    public Optional<Account> findAccountByUsername(String username) {
        return Optional.ofNullable(accounts.findByUsername(username));
    }

    @Override
    public void insertAccount(Account account) {
        accounts.insertAccount(account);
    }

    @Override
    public void updateAccount(Account account) {
        accounts.updateAccount(account);
    }

    @Override
    public Optional<Account> findAccountById(long id) {
        return Optional.ofNullable(accounts.selectById(id));
    }

    @Override
    public List<ReagentListRow> listReagentRows() {
        return reagents.listRows();
    }

    @Override
    public Optional<Reagent> findReagent(long id) {
        return Optional.ofNullable(reagents.selectById(id));
    }

    @Override
    public Optional<Reagent> findPendingBind(int slot) {
        return Optional.ofNullable(reagents.findPending(slot));
    }

    @Override
    public Optional<Reagent> findReagentByChip(String uid) {
        return Optional.ofNullable(reagents.findByChip(uid));
    }

    @Override
    public void insertReagent(Reagent reagent) {
        reagents.insertReagent(reagent);
    }

    @Override
    public void updateReagent(Reagent reagent) {
        reagents.updateReagent(reagent);
    }

    @Override
    public Optional<CabinetSession> findActiveSession(int slot) {
        return Optional.ofNullable(sessions.findActive(slot));
    }

    @Override
    public void insertSession(CabinetSession session) {
        sessions.insertSession(session);
    }

    @Override
    public void updateSession(CabinetSession session) {
        sessions.updateSession(session);
    }

    @Override
    public void insertAccess(AccessRecord record) {
        access.insertAccess(record);
    }

    @Override
    public List<AccessRecord> listAccessBySession(long sessionId) {
        return access.listBySession(sessionId);
    }

    @Override
    public void deleteAccess(long id) {
        access.removeById(id);
    }

    @Override
    public void insertAlarm(Alarm alarm) {
        alarms.insertAlarm(alarm);
    }

    @Override
    public List<Alarm> listAlarms() {
        return alarms.listRecent();
    }

    @Override
    public int acknowledge(long id, long accountId, LocalDateTime at) {
        return alarms.acknowledge(id, accountId, at);
    }

    @Override
    public void insertSample(Sample sample) {
        samples.insertSample(sample);
    }

    @Override
    public void deleteSamplesBefore(LocalDateTime cutoff) {
        samples.deleteBefore(cutoff);
    }

    @Override
    public List<Sample> latestSamples(int limit) {
        return samples.latest(limit);
    }

    @Override
    public int lastSeq() {
        DeviceState state = deviceState.selectById(1);
        return state == null ? 0 : state.getLastSeq();
    }

    @Override
    public void saveSeq(int seq) {
        deviceState.updateSeq(seq);
    }

    @Override
    public void touchHeartbeat(LocalDateTime at) {
        deviceState.touchHeartbeat(at);
    }

    @Override
    public Optional<LocalDateTime> lastHeartbeat() {
        DeviceState state = deviceState.selectById(1);
        if (state == null || state.getLastHeartbeat() == null) {
            return Optional.empty();
        }
        return Optional.of(state.getLastHeartbeat());
    }
}
