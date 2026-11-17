package edu.whpu.reagent.service;

import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.domain.Reagent;
import edu.whpu.reagent.domain.Texts;
import edu.whpu.reagent.persistence.CabinetRepository;
import edu.whpu.reagent.persistence.ReagentListRow;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class CatalogService {

    private final CabinetRepository repository;
    private final java.time.Clock clock;

    public CatalogService(CabinetRepository repository, java.time.Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    public List<ReagentView> list() {
        List<ReagentView> views = new ArrayList<>();
        for (ReagentListRow row : repository.listReagentRows()) {
            List<String> handlers = new ArrayList<>();
            if (row.getHandler1() != null && !row.getHandler1().isBlank()) {
                handlers.add(row.getHandler1());
            }
            if (row.getHandler2() != null && !row.getHandler2().isBlank()) {
                handlers.add(row.getHandler2());
            }
            views.add(new ReagentView(
                    row.getId(),
                    row.getName(),
                    Texts.levelLabel(row.getLevel()),
                    row.getSlotNo(),
                    Texts.statusLabel(row.getStatus()),
                    handlers,
                    row.getOccurredAt() == null ? null : row.getOccurredAt().toString(),
                    row.getChipUid()
            ));
        }
        return views;
    }

    @Transactional
    public Outcome register(String name, String levelRaw, int slot) {
        if (name == null || name.isBlank()) {
            return Outcome.of("bad_request", "请填写名称");
        }
        String trimmed = name.trim();
        if (trimmed.length() > 128) {
            return Outcome.of("bad_request", "名称过长");
        }
        if (slot != 1 && slot != 2) {
            return Outcome.of("bad_request", "格位只有第一格和第二格");
        }
        String level = Texts.normalizeLevel(levelRaw);
        if (level == null) {
            return Outcome.of("bad_request", "等级只取低、中、高");
        }
        if (!Texts.levelMatches(level, slot)) {
            return Outcome.of("level_cell_mismatch", "低和中放第一格，高放第二格");
        }
        if (repository.findPendingBind(slot).isPresent()) {
            return Outcome.of("pending_exists", "这一格已有一条待绑定");
        }
        Reagent reagent = new Reagent();
        reagent.setName(trimmed);
        reagent.setLevel(level);
        reagent.setSlotNo(slot);
        reagent.setStatus("pending");
        reagent.setUpdatedAt(LocalDateTime.now(clock));
        repository.insertReagent(reagent);
        return Outcome.of("ok", "已登记，等待放入");
    }

    public List<AlarmView> alarms() {
        List<AlarmView> views = new ArrayList<>();
        repository.listAlarms().forEach(alarm -> views.add(new AlarmView(
                alarm.getId(),
                alarm.getAlarmType(),
                Texts.alarmLabel(alarm.getAlarmType()),
                alarm.getChipUid(),
                alarm.getSlotNo(),
                alarm.getMessage(),
                alarm.getCreatedAt() == null ? null : alarm.getCreatedAt().toString(),
                alarm.isAcknowledged()
        )));
        return views;
    }

    @Transactional
    public Outcome acknowledge(long alarmId, String username) {
        var account = repository.findAccountByUsername(username).orElse(null);
        if (account == null) {
            return Outcome.of("unauthorized", "请先登录");
        }
        int updated = repository.acknowledge(alarmId, account.getId(), LocalDateTime.now(clock));
        if (updated == 0) {
            return Outcome.of("not_found", "没有这条未确认的告警");
        }
        return Outcome.of("ok", "已确认");
    }

    public record ReagentView(
            long id,
            String name,
            String level,
            int slot,
            String status,
            List<String> handlers,
            String at,
            String chipUid
    ) {
    }

    public record AlarmView(
            long id,
            String code,
            String type,
            String chipUid,
            Integer slot,
            String message,
            String at,
            boolean acknowledged
    ) {
    }
}
