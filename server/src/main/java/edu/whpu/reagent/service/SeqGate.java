package edu.whpu.reagent.service;

import edu.whpu.reagent.persistence.CabinetRepository;
import org.springframework.stereotype.Component;

@Component
public class SeqGate {

    private final CabinetRepository repository;

    public SeqGate(CabinetRepository repository) {
        this.repository = repository;
    }

    public void consume(int seq) {
        if (seq <= 0) {
            throw new BusinessException("bad_request", "序号不正确");
        }
        if (seq <= repository.lastSeq()) {
            throw new BusinessException("replay", "重复序号");
        }
        repository.saveSeq(seq);
    }
}
