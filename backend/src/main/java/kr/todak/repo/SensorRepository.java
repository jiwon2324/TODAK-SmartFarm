package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface SensorRepository extends JpaRepository<Sensor, Integer> {
    List<Sensor> findByFarmIdOrderBySensorId(Integer farmId);
    Optional<Sensor> findByFarmIdAndSensorCode(Integer farmId, String code);
    List<Sensor> findByFarmIdAndMetric(Integer farmId, String metric);
}
