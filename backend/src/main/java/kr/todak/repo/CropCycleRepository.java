package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface CropCycleRepository extends JpaRepository<CropCycle, Integer> {
    Optional<CropCycle> findFirstByFarmIdAndStatusOrderByCycleIdDesc(Integer farmId, String status);
    List<CropCycle> findByStatus(String status);
}
