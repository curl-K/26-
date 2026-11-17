package edu.whpu.reagent.domain;

public final class EnvLimits {

    private EnvLimits() {
    }

    public static boolean tempOver(Double value) {
        return value != null && (value < 15 || value > 30);
    }

    public static boolean humidityOver(Double value) {
        return value != null && (value < 20 || value > 70);
    }

    public static boolean tvocOver(Integer value) {
        return value != null && value > 1000;
    }

    public static boolean eco2Over(Integer value) {
        return value != null && value > 1500;
    }
}
