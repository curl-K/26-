package edu.whpu.reagent.domain;

public record Outcome(String result, String message) {

    public static Outcome of(String result, String message) {
        return new Outcome(result, message);
    }
}
