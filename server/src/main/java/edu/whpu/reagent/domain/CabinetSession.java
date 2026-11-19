package edu.whpu.reagent.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import java.time.LocalDateTime;

@TableName("cabinet_session")
public class CabinetSession {

    @TableId(type = IdType.AUTO)
    private Long id;
    private int slotNo;
    private String state;
    private Long firstAccountId;
    private Long secondAccountId;
    private String firstName;
    private String secondName;
    private LocalDateTime startedAt;
    private LocalDateTime openedAt;
    private LocalDateTime expiresAt;
    private LocalDateTime closedAt;
    private String closeReason;
    private String lastReading;
    private int streak;
    private String presentUids = "";
    private String removedUids = "";
    private String ignoredUids = "";
    private boolean suppressed;
    private boolean dualAlarm;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public int getSlotNo() {
        return slotNo;
    }

    public void setSlotNo(int slotNo) {
        this.slotNo = slotNo;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public Long getFirstAccountId() {
        return firstAccountId;
    }

    public void setFirstAccountId(Long firstAccountId) {
        this.firstAccountId = firstAccountId;
    }

    public Long getSecondAccountId() {
        return secondAccountId;
    }

    public void setSecondAccountId(Long secondAccountId) {
        this.secondAccountId = secondAccountId;
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getSecondName() {
        return secondName;
    }

    public void setSecondName(String secondName) {
        this.secondName = secondName;
    }

    public LocalDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(LocalDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public LocalDateTime getOpenedAt() {
        return openedAt;
    }

    public void setOpenedAt(LocalDateTime openedAt) {
        this.openedAt = openedAt;
    }

    public LocalDateTime getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(LocalDateTime expiresAt) {
        this.expiresAt = expiresAt;
    }

    public LocalDateTime getClosedAt() {
        return closedAt;
    }

    public void setClosedAt(LocalDateTime closedAt) {
        this.closedAt = closedAt;
    }

    public String getCloseReason() {
        return closeReason;
    }

    public void setCloseReason(String closeReason) {
        this.closeReason = closeReason;
    }

    public String getLastReading() {
        return lastReading;
    }

    public void setLastReading(String lastReading) {
        this.lastReading = lastReading;
    }

    public int getStreak() {
        return streak;
    }

    public void setStreak(int streak) {
        this.streak = streak;
    }

    public String getPresentUids() {
        return presentUids;
    }

    public void setPresentUids(String presentUids) {
        this.presentUids = presentUids;
    }

    public String getRemovedUids() {
        return removedUids;
    }

    public void setRemovedUids(String removedUids) {
        this.removedUids = removedUids;
    }

    public String getIgnoredUids() {
        return ignoredUids;
    }

    public void setIgnoredUids(String ignoredUids) {
        this.ignoredUids = ignoredUids;
    }

    public boolean isSuppressed() {
        return suppressed;
    }

    public void setSuppressed(boolean suppressed) {
        this.suppressed = suppressed;
    }

    public boolean isDualAlarm() {
        return dualAlarm;
    }

    public void setDualAlarm(boolean dualAlarm) {
        this.dualAlarm = dualAlarm;
    }
}
