package edu.whpu.reagent.domain;

public final class Texts {

    private Texts() {
    }

    public static String normalizeLevel(String raw) {
        if (raw == null) {
            return null;
        }
        return switch (raw.trim()) {
            case "低", "low", "LOW" -> "low";
            case "中", "mid", "MID" -> "mid";
            case "高", "high", "HIGH" -> "high";
            default -> null;
        };
    }

    public static boolean levelMatches(String level, int slot) {
        if (slot == 1) {
            return "low".equals(level) || "mid".equals(level);
        }
        if (slot == 2) {
            return "high".equals(level);
        }
        return false;
    }

    public static String levelLabel(String level) {
        return switch (level) {
            case "low" -> "低";
            case "mid" -> "中";
            case "high" -> "高";
            default -> level;
        };
    }

    public static String statusLabel(String status) {
        return switch (status) {
            case "pending" -> "待绑定";
            case "in_cabinet" -> "在柜";
            case "taken_out" -> "已取出";
            default -> status;
        };
    }

    public static String alarmLabel(String code) {
        return switch (code) {
            case "unbound_chip" -> "未登记芯片";
            case "level_cell_mismatch" -> "格位不符";
            case "dual_chip" -> "一格两瓶";
            case "env" -> "环境越限";
            default -> code;
        };
    }
}
