package edu.whpu.reagent;

import edu.whpu.reagent.domain.Account;
import edu.whpu.reagent.service.CatalogService;
import edu.whpu.reagent.service.ChipService;
import edu.whpu.reagent.service.ConfirmService;
import edu.whpu.reagent.service.EnvironmentService;
import edu.whpu.reagent.service.SeqGate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.time.LocalDateTime;
import java.time.ZoneId;

final class Lab {

    final MemoryCabinetRepository repo = new MemoryCabinetRepository();
    final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    final MutableClock clock = new MutableClock(LocalDateTime.of(2026, 11, 17, 12, 0), ZoneId.of("Asia/Shanghai"));
    final SeqGate seqGate = new SeqGate(repo);
    final ConfirmService confirm = new ConfirmService(repo, seqGate, encoder, clock);
    final ChipService chip = new ChipService(repo, seqGate, clock);
    final CatalogService catalog = new CatalogService(repo, clock);
    final EnvironmentService environment = new EnvironmentService(repo, seqGate, clock);
    private int seq = 0;

    Lab() {
        taker("chen", "陈", "chen123");
        taker("li", "李", "li123");
        account("manager", "管理人", "manager123", "manager");
    }

    int seq() {
        return ++seq;
    }

    private void taker(String username, String name, String password) {
        account(username, name, password, "taker");
    }

    private void account(String username, String name, String password, String role) {
        Account account = new Account();
        account.setUsername(username);
        account.setDisplayName(name);
        account.setRole(role);
        account.setPasswordHash(encoder.encode(password));
        repo.insertAccount(account);
    }
}
