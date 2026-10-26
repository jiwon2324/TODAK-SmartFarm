package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface UserFarmRepository extends JpaRepository<UserFarm, UserFarm.Key> {
    List<UserFarm> findByUserId(Integer userId);
    List<UserFarm> findByFarmId(Integer farmId);
    boolean existsByUserIdAndFarmId(Integer userId, Integer farmId);
    void deleteByUserId(Integer userId);
}
