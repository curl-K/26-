package edu.whpu.reagent.web;

import edu.whpu.reagent.domain.Outcome;
import edu.whpu.reagent.service.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    @ResponseStatus(HttpStatus.OK)
    public Outcome business(BusinessException exception) {
        return Outcome.of(exception.getResult(), exception.getMessage());
    }
}
