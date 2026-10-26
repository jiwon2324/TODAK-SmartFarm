package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface DeviceRepository extends JpaRepository<Device, Integer> {
    List<Device> findByFarmIdOrderByDeviceId(Integer farmId);
    Optional<Device> findByFarmIdAndDeviceCode(Integer farmId, String code);

    long countByZoneId(Integer zoneId);
}
