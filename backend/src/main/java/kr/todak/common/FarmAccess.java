package kr.todak.common;

import kr.todak.domain.Device;
import kr.todak.domain.Sensor;
import kr.todak.repo.DeviceRepository;
import kr.todak.repo.FarmRepository;
import kr.todak.repo.SensorRepository;
import kr.todak.repo.UserFarmRepository;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 농장 단위 접근 제어. 관리자는 모든 농장, 농가는 TB_USER_FARM에 등록된 농장만 접근한다.
 * 화면 메뉴를 숨기는 것과 별개로 모든 농장 범위 API가 이 검사를 거친다. (인수 기준 6)
 */
@Component
public class FarmAccess {
    private final UserFarmRepository userFarms;
    private final FarmRepository farms;
    private final SensorRepository sensors;
    private final DeviceRepository devices;

    public FarmAccess(UserFarmRepository userFarms, FarmRepository farms, SensorRepository sensors, DeviceRepository devices) {
        this.userFarms = userFarms;
        this.farms = farms;
        this.sensors = sensors;
        this.devices = devices;
    }

    public CurrentUser user() {
        Object p = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        if (p instanceof CurrentUser cu) {
            return cu;
        }
        throw ApiException.forbidden();
    }

    public List<Integer> allowedFarmIds() {
        CurrentUser u = user();
        if (u.isAdmin()) {
            return farms.findAll().stream().map(f -> f.getFarmId()).toList();
        }
        return userFarms.findByUserId(u.userId()).stream().map(uf -> uf.getFarmId()).toList();
    }

    public void check(Integer farmId) {
        CurrentUser u = user();
        if (u.isAdmin()) {
            if (!farms.existsById(farmId)) {
                throw ApiException.notFound("농장");
            }
            return;
        }
        if (!userFarms.existsByUserIdAndFarmId(u.userId(), farmId)) {
            throw ApiException.forbidden();
        }
    }

    /** 조회 전용(VIEWER) 계정은 제어·설정 변경을 할 수 없다 (계획서 표 41, API-12 403) */
    public void requireOperator() {
        if ("VIEWER".equals(user().role())) {
            throw new ApiException(org.springframework.http.HttpStatus.FORBIDDEN, "FORBIDDEN", "조회 전용 계정은 제어나 설정 변경을 할 수 없습니다");
        }
    }

    public Sensor sensor(Integer sensorId) {
        Sensor s = sensors.findById(sensorId).orElseThrow(() -> ApiException.notFound("센서"));
        check(s.getFarmId());
        return s;
    }

    public Device device(Integer deviceId) {
        Device d = devices.findById(deviceId).orElseThrow(() -> ApiException.notFound("장치"));
        check(d.getFarmId());
        return d;
    }
}
