package edu.whpu.reagent.device;

import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.service.ChipService;
import edu.whpu.reagent.service.ConfirmService;
import edu.whpu.reagent.service.EnvironmentService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/device")
public class DeviceController {

    private static final Logger log = LoggerFactory.getLogger(DeviceController.class);

    private final ConfirmService confirmService;
    private final ChipService chipService;
    private final EnvironmentService environmentService;

    public DeviceController(ConfirmService confirmService, ChipService chipService, EnvironmentService environmentService) {
        this.confirmService = confirmService;
        this.chipService = chipService;
        this.environmentService = environmentService;
    }

    @PostMapping("/heartbeat")
    public Outcome heartbeat(@RequestBody SeqBody body) {
        Outcome outcome = environmentService.heartbeat(body.seq());
        log.info("heartbeat result={}", outcome.result());
        return outcome;
    }

    @PostMapping("/confirm")
    public Outcome confirm(@RequestBody ConfirmBody body) {
        Outcome outcome = confirmService.confirm(body.seq(), body.slot(), body.username(), body.password());
        log.info("confirm slot={} user={} result={}", body.slot(), body.username(), outcome.result());
        return outcome;
    }

    @PostMapping("/chip")
    public Outcome chip(@RequestBody ChipBody body) {
        Outcome outcome = chipService.observe(body.seq(), body.slot(), body.uid());
        log.info("chip slot={} result={}", body.slot(), outcome.result());
        return outcome;
    }

    @PostMapping("/session/end")
    public Outcome end(@RequestBody EndBody body) {
        Outcome outcome = chipService.end(body.seq(), body.slot(), body.reason());
        log.info("session end slot={} result={}", body.slot(), outcome.result());
        return outcome;
    }

    @PostMapping("/environment")
    public Outcome environment(@RequestBody SampleBody body) {
        Outcome outcome = environmentService.record(
                body.seq(), body.device(), body.slot(), body.temperature(), body.humidity(), body.tvoc(), body.eco2());
        log.info("environment result={}", outcome.result());
        return outcome;
    }

    public record SeqBody(int seq) {
    }

    public record ConfirmBody(int seq, int slot, String username, String password) {
    }

    public record ChipBody(int seq, int slot, String uid) {
    }

    public record EndBody(int seq, int slot, String reason) {
    }

    public record SampleBody(int seq, String device, Integer slot, Double temperature, Double humidity, Integer tvoc, Integer eco2) {
    }
}
