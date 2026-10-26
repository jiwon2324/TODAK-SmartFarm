package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface SensorDataRepository extends JpaRepository<SensorData, Long> {
    boolean existsByMsgId(String msgId);
    boolean existsBySensorIdAndMeasuredAt(Integer sensorId, LocalDateTime t);
    Optional<SensorData> findFirstBySensorIdOrderByMeasuredAtDesc(Integer sensorId);
    List<SensorData> findBySensorIdAndMeasuredAtBetweenOrderByMeasuredAt(Integer sensorId, LocalDateTime from, LocalDateTime to);
    long countByReceivedAtAfter(LocalDateTime t);
    long countBySensorIdAndReceivedAtAfter(Integer sensorId, LocalDateTime t);
    @Query("select max(d.receivedAt) from SensorData d") LocalDateTime lastReceivedAt();
}
