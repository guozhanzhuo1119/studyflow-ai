package com.studyflow;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.studyflow.mapper")
public class StudyFlowApplication {

    public static void main(String[] args) {
        SpringApplication.run(StudyFlowApplication.class, args);
    }
}
