package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface AlertRepository extends JpaRepository<Alert, Long> {
    Optional<Alert> findFirstByDedupeKeyAndStatusNotOrderByAlertIdDesc(String key, String status);
    List<Alert> findByDedupeKeyAndStatusNot(String key, String status);
    Page<Alert> findByFarmIdInOrderByAlertIdDesc(Collection<Integer> farmIds, Pageable p);
    Page<Alert> findByFarmIdInAndStatusOrderByAlertIdDesc(Collection<Integer> farmIds, String status, Pageable p);
    long countByFarmIdInAndStatusNot(Collection<Integer> farmIds, String status);
}
