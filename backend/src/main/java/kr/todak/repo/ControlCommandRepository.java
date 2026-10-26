package kr.todak.repo;

import kr.todak.domain.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.*;
import java.util.*;

public interface ControlCommandRepository extends JpaRepository<ControlCommand, Long> {
    List<ControlCommand> findByStatusIn(Collection<String> statuses);
    Optional<ControlCommand> findByIdempotencyKey(String key);
    boolean existsByDeviceIdAndStatusIn(Integer deviceId, Collection<String> statuses);
    long countByDeviceIdAndSourceAndActionAndRequestedAtAfter(Integer deviceId, String source, String action, LocalDateTime t);
    Optional<ControlCommand> findFirstByDeviceIdAndStatusOrderByCommandIdDesc(Integer deviceId, String status);
    Page<ControlCommand> findByDeviceIdInOrderByCommandIdDesc(Collection<Integer> deviceIds, Pageable p);
    long countByRequestedAtAfterAndStatus(LocalDateTime t, String status);
    Optional<ControlCommand> findFirstByDeviceIdAndSourceAndActionOrderByCommandIdDesc(Integer deviceId, String source, String action);
    long countByDeviceIdAndSourceAndRequestedAtAfter(Integer deviceId, String source, LocalDateTime t);
}
