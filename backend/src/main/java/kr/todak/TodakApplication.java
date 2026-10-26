package kr.todak;

import jakarta.annotation.PostConstruct;
import kr.todak.config.TodakProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

import java.util.TimeZone;

@SpringBootApplication
@EnableConfigurationProperties(TodakProperties.class)
public class TodakApplication {

    @PostConstruct
    void timezone() {
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Seoul"));
    }

    public static void main(String[] args) {
        SpringApplication.run(TodakApplication.class, args);
    }
}
