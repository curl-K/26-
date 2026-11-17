package edu.whpu.reagent.web;

import edu.whpu.reagent.service.EnvironmentService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class EnvironmentController {

    private final EnvironmentService environmentService;

    public EnvironmentController(EnvironmentService environmentService) {
        this.environmentService = environmentService;
    }

    @GetMapping("/environment")
    public EnvironmentService.EnvView environment() {
        return environmentService.view();
    }
}
