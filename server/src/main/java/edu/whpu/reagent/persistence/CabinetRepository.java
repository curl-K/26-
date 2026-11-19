package edu.whpu.reagent.persistence;

import edu.whpu.reagent.domain.AccessRecord;
import edu.whpu.reagent.domain.Account;
import edu.whpu.reagent.domain.Alarm;
import edu.whpu.reagent.domain.CabinetSession;
import edu.whpu.reagent.domain.Reagent;
import edu.whpu.reagent.domain.Sample;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface CabinetRepository {

    Optional<Account> findAccountByUsername(String username);

    void insertAccount(Account account);

    List<Account> listAccounts();

    void updateAccount(Account account);

    Optional<Account> findAccountById(long id);

    List<ReagentListRow> listReagentRows();

    Optional<Reagent> findReagent(long id);

    Optional<Reagent> findPendingBind(int slot);

    Optional<Reagent> findReagentByChip(String uid);

    void insertReagent(Reagent reagent);

    void updateReagent(Reagent reagent);

    Optional<CabinetSession> findActiveSession(int slot);

    void insertSession(CabinetSession session);

    void updateSession(CabinetSession session);

    void insertAccess(AccessRecord record);

    List<AccessRecord> listAccessBySession(long sessionId);

    void deleteAccess(long id);

    void deleteAccessByReagent(long reagentId);

    void deleteReagent(long id);

    void insertAlarm(Alarm alarm);

    List<Alarm> listAlarms();

    int acknowledge(long id, long accountId, LocalDateTime at);

    void insertSample(Sample sample);

    void deleteSamplesBefore(LocalDateTime cutoff);

    List<Sample> latestSamples(int limit);

    int lastSeq();

    void saveSeq(int seq);

    void touchHeartbeat(LocalDateTime at);

    Optional<LocalDateTime> lastHeartbeat();
}
