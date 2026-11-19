package edu.whpu.reagent.service;

import edu.whpu.reagent.domain.Account;
import edu.whpu.reagent.domain.CabinetSession;
import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.persistence.CabinetRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Service
public class ConfirmService {

    private final CabinetRepository repository;
    private final SeqGate seqGate;
    private final PasswordEncoder passwordEncoder;
    private final java.time.Clock clock;

    public ConfirmService(CabinetRepository repository, SeqGate seqGate, PasswordEncoder passwordEncoder, java.time.Clock clock) {
        this.repository = repository;
        this.seqGate = seqGate;
        this.passwordEncoder = passwordEncoder;
        this.clock = clock;
    }

    @Transactional
    public Outcome confirm(int seq, int slot, String username, String password) {
        if (slot != 1 && slot != 2) {
            return Outcome.of("bad_request", "格位只有第一格和第二格");
        }
        if (username == null || username.isBlank() || password == null || password.isEmpty()) {
            return Outcome.of("bad_request", "请填写账号和密码");
        }
        seqGate.consume(seq);
        LocalDateTime now = LocalDateTime.now(clock);
        CabinetSession active = repository.findActiveSession(slot).orElse(null);
        if (active != null && "open".equals(active.getState())) {
            if (Sessions.openExpired(active, now)) {
                Sessions.close(active, now, "timeout");
                repository.updateSession(active);
            } else {
                return Outcome.of("session_open", "上一次开格还未结束");
            }
            active = null;
        }
        if (active != null && "waiting".equals(active.getState())) {
            if (Sessions.waitingExpired(active, now)) {
                Sessions.close(active, now, "timeout");
                repository.updateSession(active);
                return Outcome.of("expired", "等待已超时，请重新确认");
            }
            return secondPerson(active, username.trim(), password, now);
        }
        return firstPerson(slot, username.trim(), password, now);
    }

    private Outcome firstPerson(int slot, String username, String password, LocalDateTime now) {
        AuthResult auth = check(username, password, now);
        if (auth.failure != null) {
            return auth.failure;
        }
        CabinetSession session = newSession(slot, auth.account, now);
        if (slot == 1) {
            session.setState("open");
            session.setOpenedAt(now);
            repository.insertSession(session);
            return Outcome.of("allow", "可以开格");
        }
        session.setState("waiting");
        session.setExpiresAt(now.plusSeconds(60));
        repository.insertSession(session);
        return Outcome.of("need_second", "请另一名取用人在六十秒内确认");
    }

    private Outcome secondPerson(CabinetSession waiting, String username, String password, LocalDateTime now) {
        AuthResult auth = check(username, password, now);
        if (auth.failure != null) {
            Sessions.close(waiting, now, auth.failure.result());
            repository.updateSession(waiting);
            return auth.failure;
        }
        if (auth.account.getId().equals(waiting.getFirstAccountId())) {
            Sessions.close(waiting, now, "same_account");
            repository.updateSession(waiting);
            return Outcome.of("same_account", "两次是同一账号，请换人后重新确认");
        }
        waiting.setState("open");
        waiting.setSecondAccountId(auth.account.getId());
        waiting.setSecondName(auth.account.getDisplayName());
        waiting.setOpenedAt(now);
        waiting.setExpiresAt(null);
        repository.updateSession(waiting);
        return Outcome.of("allow", "可以开格");
    }

    private CabinetSession newSession(int slot, Account account, LocalDateTime now) {
        CabinetSession session = new CabinetSession();
        session.setSlotNo(slot);
        session.setFirstAccountId(account.getId());
        session.setFirstName(account.getDisplayName());
        session.setStartedAt(now);
        Sessions.blankChipState(session);
        return session;
    }

    private AuthResult check(String username, String password, LocalDateTime now) {
        Account account = repository.findAccountByUsername(username).orElse(null);
        if (account == null || !"taker".equals(account.getRole())) {
            return AuthResult.fail(Outcome.of("bad_password", "账号或密码错误"));
        }
        if (account.getLockedUntil() != null && account.getLockedUntil().isAfter(now)) {
            return AuthResult.fail(Outcome.of("locked", "连续三次密码错误，暂时锁定"));
        }
        if (!passwordEncoder.matches(password, account.getPasswordHash())) {
            int attempts = account.getFailedAttempts() + 1;
            if (attempts >= 3) {
                account.setFailedAttempts(0);
                account.setLockedUntil(now.plusSeconds(60));
                repository.updateAccount(account);
                return AuthResult.fail(Outcome.of("locked", "连续三次密码错误，暂时锁定"));
            }
            account.setFailedAttempts(attempts);
            account.setLockedUntil(null);
            repository.updateAccount(account);
            return AuthResult.fail(Outcome.of("bad_password", "账号或密码错误"));
        }
        account.setFailedAttempts(0);
        account.setLockedUntil(null);
        repository.updateAccount(account);
        return AuthResult.ok(account);
    }

    private static final class AuthResult {
        private final Outcome failure;
        private final Account account;

        private AuthResult(Outcome failure, Account account) {
            this.failure = failure;
            this.account = account;
        }

        private static AuthResult fail(Outcome outcome) {
            return new AuthResult(outcome, null);
        }

        private static AuthResult ok(Account account) {
            return new AuthResult(null, account);
        }
    }
}
