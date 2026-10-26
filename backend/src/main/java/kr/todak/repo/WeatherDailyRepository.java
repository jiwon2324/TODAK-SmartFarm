package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface WeatherDailyRepository extends JpaRepository<WeatherDaily, WeatherDaily.Key> {
    List<WeatherDaily> findByStationIdAndObsDateBetweenOrderByObsDate(String stationId, LocalDate from, LocalDate to);
}
