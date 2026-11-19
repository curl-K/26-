package edu.whpu.reagent.domain;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public final class Uids {

    private Uids() {
    }

    public static List<String> split(String raw) {
        if (raw == null || raw.isBlank()) {
            return new ArrayList<>();
        }
        return new ArrayList<>(Arrays.asList(raw.split(",")));
    }

    public static String join(List<String> values) {
        return String.join(",", values);
    }

    public static boolean contains(String raw, String uid) {
        return split(raw).contains(uid);
    }
}
