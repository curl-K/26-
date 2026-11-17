package edu.whpu.reagent;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("edu.whpu.reagent.persistence.mapper")
public class ReagentApplication {

    public static void main(String[] args) {
        SpringApplication.run(ReagentApplication.class, args);
    }
}
