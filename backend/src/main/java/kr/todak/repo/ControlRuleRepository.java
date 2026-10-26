package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface ControlRuleRepository extends JpaRepository<ControlRule, Integer> {
    List<ControlRule> findByFarmIdAndIsEnabledTrueOrderByPriority(Integer farmId);
    List<ControlRule> findByFarmIdOrderByPriority(Integer farmId);
}
