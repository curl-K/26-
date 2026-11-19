package edu.whpu.reagent.web;

import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.service.CatalogService;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class CatalogController {

    private final CatalogService catalog;

    public CatalogController(CatalogService catalog) {
        this.catalog = catalog;
    }

    @GetMapping("/reagents")
    public Map<String, Object> list() {
        return Map.of("items", catalog.list());
    }

    @PostMapping("/reagents")
    public Outcome register(@RequestBody RegisterRequest request) {
        if (request.slot() == null) {
            return Outcome.of("bad_request", "请选择格");
        }
        return catalog.register(request.name(), request.level(), request.slot());
    }

    @DeleteMapping("/reagents/{id}")
    public Outcome delete(@PathVariable long id) {
        return catalog.delete(id);
    }

    @GetMapping("/accounts")
    public Map<String, Object> accounts() {
        return Map.of("items", catalog.people());
    }
    @GetMapping("/alarms")
    public Map<String, Object> alarms() {
        return Map.of("items", catalog.alarms());
    }

    @PostMapping("/alarms/{id}/ack")
    public Outcome acknowledge(@PathVariable long id) {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return catalog.acknowledge(id, username);
    }

    public record RegisterRequest(String name, String level, Integer slot) {
    }
}
