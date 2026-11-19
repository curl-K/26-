package edu.whpu.reagent.persistence;

import java.time.LocalDateTime;

public class ReagentListRow {

    private Long id;
    private String name;
    private String level;
    private int slotNo;
    private String status;
    private String chipUid;
    private String handler1;
    private String handler2;
    private LocalDateTime occurredAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public int getSlotNo() {
        return slotNo;
    }

    public void setSlotNo(int slotNo) {
        this.slotNo = slotNo;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getChipUid() {
        return chipUid;
    }

    public void setChipUid(String chipUid) {
        this.chipUid = chipUid;
    }

    public String getHandler1() {
        return handler1;
    }

    public void setHandler1(String handler1) {
        this.handler1 = handler1;
    }

    public String getHandler2() {
        return handler2;
    }

    public void setHandler2(String handler2) {
        this.handler2 = handler2;
    }

    public LocalDateTime getOccurredAt() {
        return occurredAt;
    }

    public void setOccurredAt(LocalDateTime occurredAt) {
        this.occurredAt = occurredAt;
    }
}
