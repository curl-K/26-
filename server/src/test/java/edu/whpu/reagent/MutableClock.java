package edu.whpu.reagent;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

final class MutableClock extends Clock {

    private final ZoneId zone;
    private Instant instant;

    MutableClock(LocalDateTime time, ZoneId zone) {
        this.zone = zone;
        this.instant = time.atZone(zone).toInstant();
    }

    void advance(Duration duration) {
        instant = instant.plus(duration);
    }

    @Override
    public ZoneId getZone() {
        return zone;
    }

    @Override
    public Clock withZone(ZoneId zone) {
        return new MutableClock(LocalDateTime.ofInstant(instant, zone), zone);
    }

    @Override
    public Instant instant() {
        return instant;
    }
}
