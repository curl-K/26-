package edu.whpu.reagent.service;

import edu.whpu.reagent.domain.Alarm;
import edu.whpu.reagent.domain.EnvLimits;
import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.domain.Sample;
import edu.whpu.reagent.persistence.CabinetRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.Predicate;

@Service
public class EnvironmentService {

    private final CabinetRepository repository;
    private final SeqGate seqGate;
    private final java.time.Clock clock;

    public EnvironmentService(CabinetRepository repository, SeqGate seqGate, java.time.Clock clock) {
        this.repository = repository;
        this.seqGate = seqGate;
        this.clock = clock;
    }

    @Transactional
    public Outcome record(int seq, String device, Integer slot, Double temperature, Double humidity, Integer tvoc, Integer eco2) {
        if (temperature == null && humidity == null && tvoc == null && eco2 == null) {
            return Outcome.of("bad_request", "没有采样值");
        }
        seqGate.consume(seq);
        LocalDateTime now = LocalDateTime.now(clock);
        Sample sample = new Sample();
        sample.setDeviceName(device == null || device.isBlank() ? "env-1" : device.trim());
        sample.setSlotNo(slot);
        sample.setTemperature(temperature);
        sample.setHumidity(humidity);
        sample.setTvoc(tvoc);
        sample.setEco2(eco2);
        sample.setSampledAt(now);
        repository.insertSample(sample);
        repository.deleteSamplesBefore(now.minusDays(30));
        raiseIfThird(slot, "温度连续三次越出 15–30 ℃", row -> EnvLimits.tempOver(row.getTemperature()));
        raiseIfThird(slot, "湿度连续三次越出 20–70 %RH", row -> EnvLimits.humidityOver(row.getHumidity()));
        raiseIfThird(slot, "TVOC 连续三次高于 1000 ppb", sampleRow -> EnvLimits.tvocOver(sampleRow.getTvoc()));
        raiseIfThird(slot, "eCO2 连续三次高于 1500", sampleRow -> EnvLimits.eco2Over(sampleRow.getEco2()));
        return Outcome.of("ok", "已记录采样");
    }

    public EnvView view() {
        LocalDateTime now = LocalDateTime.now(clock);
        LocalDateTime beat = repository.lastHeartbeat().orElse(null);
        boolean online = beat != null && !beat.isBefore(now.minusSeconds(30));
        List<Sample> latest = repository.latestSamples(1);
        Reading reading = null;
        if (!latest.isEmpty()) {
            Sample sample = latest.get(0);
            reading = new Reading(
                    sample.getTemperature(),
                    sample.getHumidity(),
                    sample.getTvoc(),
                    sample.getEco2(),
                    sample.getSampledAt().toString(),
                    EnvLimits.tempOver(sample.getTemperature()),
                    EnvLimits.humidityOver(sample.getHumidity()),
                    EnvLimits.tvocOver(sample.getTvoc()),
                    EnvLimits.eco2Over(sample.getEco2())
            );
        }
        List<Sample> recent = new ArrayList<>(repository.latestSamples(60));
        Collections.reverse(recent);
        List<HistoryPoint> history = new ArrayList<>();
        for (Sample sample : recent) {
            history.add(new HistoryPoint(
                    sample.getSampledAt().toString(),
                    sample.getTemperature(),
                    sample.getHumidity(),
                    sample.getTvoc(),
                    sample.getEco2()
            ));
        }
        return new EnvView(online, beat == null ? null : beat.toString(), reading, history);
    }

    @Transactional
    public Outcome heartbeat(int seq) {
        seqGate.consume(seq);
        repository.touchHeartbeat(LocalDateTime.now(clock));
        return Outcome.of("ok", "在线");
    }

    private void raiseIfThird(Integer slot, String message, Predicate<Sample> over) {
        List<Sample> recent = repository.latestSamples(4);
        if (recent.size() < 3) {
            return;
        }
        if (!over.test(recent.get(0)) || !over.test(recent.get(1)) || !over.test(recent.get(2))) {
            return;
        }
        if (recent.size() >= 4 && over.test(recent.get(3))) {
            return;
        }
        Alarm alarm = new Alarm();
        alarm.setAlarmType("env");
        alarm.setSlotNo(slot);
        alarm.setMessage(message);
        alarm.setAcknowledged(false);
        alarm.setCreatedAt(recent.get(0).getSampledAt());
        repository.insertAlarm(alarm);
    }

    public record Reading(
            Double temperature,
            Double humidity,
            Integer tvoc,
            Integer eco2,
            String at,
            boolean tempOver,
            boolean humidityOver,
            boolean tvocOver,
            boolean eco2Over
    ) {
    }

    public record HistoryPoint(String at, Double temperature, Double humidity, Integer tvoc, Integer eco2) {
    }

    public record EnvView(boolean online, String lastHeartbeat, Reading latest, List<HistoryPoint> history) {
    }
}
