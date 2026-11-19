package edu.whpu.reagent.service;

public class BusinessException extends RuntimeException {

    private final String result;

    public BusinessException(String result, String message) {
        super(message);
        this.result = result;
    }

    public String getResult() {
        return result;
    }
}
