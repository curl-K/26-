package edu.whpu.reagent.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import java.time.LocalDateTime;

@TableName("access_record")
public class AccessRecord {

    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long reagentId;
    private String chipUid;
    private int slotNo;
    private String action;
    private String handler1;
    private String handler2;
    private LocalDateTime occurredAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getSessionId() {
        return sessionId;
    }

    public void setSessionId(Long sessionId) {
        this.sessionId = sessionId;
    }

    public Long getReagentId() {
        return reagentId;
    }

    public void setReagentId(Long reagentId) {
        this.reagentId = reagentId;
    }

    public String getChipUid() {
        return chipUid;
    }

    public void setChipUid(String chipUid) {
        this.chipUid = chipUid;
    }

    public int getSlotNo() {
        return slotNo;
    }

    public void setSlotNo(int slotNo) {
        this.slotNo = slotNo;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
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
