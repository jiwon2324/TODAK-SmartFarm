# -*- coding: utf-8 -*-
"""API·MQTT·기술 스택·추적성 정의 (계획서·RFP·보고서 양식이 공유)."""

# (ID, 메서드, 경로, 권한, 설명, REQ, 테이블)
API = [
    ("API-01", "POST", "/api/v1/auth/login", "공개", "로그인, JWT 발급(1시간)", "F-12", "TB_USER"),
    ("API-02", "GET", "/api/v1/auth/me", "전체", "내 정보·역할", "F-12", "TB_USER"),
    ("API-03", "GET·POST", "/api/v1/users", "ADMIN", "사용자 목록·등록", "F-12", "TB_USER"),
    ("API-04", "PATCH", "/api/v1/users/{userId}", "ADMIN", "역할·활성 변경, 잠금 해제", "F-12", "TB_USER"),
    ("API-05", "GET·POST", "/api/v1/farms/{farmId}/zones", "전체·ADMIN", "구역 조회·등록", "F-13", "TB_ZONE"),
    ("API-06", "GET", "/api/v1/zones/{zoneId}/dashboard", "전체", "최신 측정값·장치 상태·미처리 알림·DLI·누적 GDD", "F-01, F-18", "TB_SENSOR_DATA, TB_DEVICE, TB_ALERT"),
    ("API-07", "GET", "/api/v1/stream?farmId=1", "전체", "SSE 구독(측정·장치·알림 이벤트)", "F-18", "-"),
    ("API-08", "GET·POST", "/api/v1/sensors", "전체·ADMIN", "센서 채널 조회·등록·구역 매핑", "F-13", "TB_SENSOR"),
    ("API-09", "GET", "/api/v1/sensors/{sensorId}/data", "전체", "기간 조회 (interval=raw|hour)", "F-10", "TB_SENSOR_DATA(_HOURLY)"),
    ("API-10", "GET", "/api/v1/zones/{zoneId}/export.csv", "전체", "CSV 다운로드", "F-10", "TB_SENSOR_DATA"),
    ("API-11", "GET", "/api/v1/devices?zoneId=", "전체", "장치 목록·상태·모드", "F-08", "TB_DEVICE"),
    ("API-12", "POST", "/api/v1/devices/{deviceId}/commands", "FARMER·ADMIN", "수동 명령 (202 + commandId)", "F-08, F-16", "TB_CONTROL_COMMAND"),
    ("API-13", "GET", "/api/v1/commands/{commandId}", "전체", "명령 상태 조회", "F-16", "TB_CONTROL_COMMAND"),
    ("API-14", "PATCH", "/api/v1/devices/{deviceId}/mode", "FARMER·ADMIN", "AUTO/MANUAL, manual_until", "F-08", "TB_DEVICE, TB_SETTING_HISTORY"),
    ("API-15", "GET", "/api/v1/control-logs", "전체", "장치 상태 이력 조회", "F-10", "TB_CONTROL_LOG"),
    ("API-16", "GET·POST", "/api/v1/crop-standards", "전체·FARMER", "기준값 조회·새 버전 등록", "F-11", "TB_CROP_STD"),
    ("API-17", "GET·PUT", "/api/v1/control-rules[/{ruleId}]", "전체·ADMIN", "자동 제어 규칙 조회·수정", "F-02~04", "TB_CONTROL_RULE"),
    ("API-18", "GET·PATCH", "/api/v1/alerts[/{alertId}]", "전체·FARMER", "알림 조회·확인·해결", "F-09", "TB_ALERT"),
    ("API-19", "GET", "/api/v1/crop-cycles/{cycleId}/gdd", "전체", "일별·누적 GDD (source=INTERNAL|EXTERNAL)", "F-14", "TB_GDD_DAILY"),
    ("API-20", "PATCH", "/api/v1/crop-cycles/{cycleId}", "FARMER·ADMIN", "정식일·Tbase·Tupper 변경 (이력 저장)", "F-14", "TB_CROP_CYCLE, TB_SETTING_HISTORY"),
    ("API-21", "POST", "/api/v1/weather/import", "ADMIN", "기상자료개방포털 CSV 업로드", "F-15", "TB_WEATHER_DAILY"),
    ("API-22", "GET", "/api/v1/weather/daily", "전체", "외부 기상 일자료 조회", "F-15", "TB_WEATHER_DAILY"),
    ("API-23", "GET·POST", "/api/v1/beehives", "전체·FARMER", "벌통 등록·교체 예정일", "F-06", "TB_BEEHIVE"),
    ("API-24", "GET", "/api/v1/image-results", "전체", "착색도 결과 조회", "F-07", "TB_IMAGE_RESULT"),
    ("API-25", "POST", "/api/v1/image-results", "분석 서비스(API Key)", "착색도 결과 등록", "F-07", "TB_IMAGE_RESULT"),
    ("API-26", "POST", "/api/v1/ingest/sensor-data", "게이트웨이(기기 토큰)", "MQTT 장애 시 HTTP 대체 수집", "F-01", "TB_SENSOR_DATA"),
    ("API-27", "POST", "/api/v1/simulator/scenarios/{name}", "ADMIN", "시뮬레이터 시나리오 실행 (B안)", "F-17", "-"),
]

MQTT = [
    ("todak/{farm}/{zone}/sensor/{sensorCode}", "GW → 서버", "1", "아니오", "1분 평균 측정값"),
    ("todak/{farm}/gw/{gw}/status", "GW → 서버", "1", "예 (LWT=offline)", "30초 하트비트, online/offline"),
    ("todak/{farm}/gw/{gw}/config", "서버 → GW", "1", "예", "기준값·안전 규칙 사본, version_no"),
    ("todak/{farm}/device/{deviceCode}/cmd", "서버 → GW", "1", "아니오", "명령 (commandId, action, durationSec)"),
    ("todak/{farm}/device/{deviceCode}/ack", "GW → 서버", "1", "아니오", "명령 결과 (commandId, result, state)"),
    ("todak/{farm}/device/{deviceCode}/state", "GW → 서버", "1", "아니오", "서버 명령 없이 바뀐 상태 (FAILSAFE·현장 수동)"),
]

ERRORS = [
    ("400", "VALIDATION_ERROR", "입력 형식·범위 오류 (예: 최소 > 최대)"),
    ("401", "UNAUTHORIZED", "토큰 없음·만료"),
    ("403", "FORBIDDEN", "역할 권한 없음 (VIEWER의 제어 요청 등)"),
    ("404", "NOT_FOUND", "대상 없음"),
    ("409", "DUPLICATE_REQUEST", "같은 idempotencyKey의 다른 요청 본문"),
    ("423", "SAFETY_LOCKED", "안전 한계(CR-05·06) 작동 중 반대 동작 수동 명령"),
    ("503", "GATEWAY_OFFLINE", "게이트웨이 오프라인으로 명령 전송 불가"),
    ("500", "INTERNAL_ERROR", "서버 오류 (traceId 포함)"),
]

STACK = [
    ("프론트엔드", "React 18, TypeScript, Vite, Recharts, MUI", "React + TS 선정, 차트는 Recharts", "컴포넌트 재사용, 타입 안정성, React 친화 차트", "Chart.js: 캔버스 기반으로 가볍지만 React 연동 코드가 늘어남"),
    ("백엔드", "Java 17, Spring Boot 3, Spring Security, Spring Data JPA", "선정", "수업·취업 수요, 인증·트랜잭션 표준 지원", "Node.js: 빠르지만 팀 숙련도·타입 안정성 낮음"),
    ("실시간", "WebSocket / SSE", "SSE", "서버 → 브라우저 단방향이면 충분, 구현·재연결 단순", "WebSocket: 양방향이 필요해지면 전환"),
    ("IoT 연동", "MQTT (Mosquitto 2) + Spring Integration MQTT", "선정", "경량·QoS·LWT로 단절 감지, IoT 표준", "HTTP 폴링: 단순하지만 실시간성·전력 불리 (대체 수집 API로만 유지)"),
    ("DB", "MySQL 8 + Flyway", "선정", "과제 지정, 스키마 버전 관리", "PostgreSQL+TimescaleDB: 시계열에 유리하나 범위 밖"),
    ("분석", "Python 3.11, OpenCV, pandas", "선정", "영상 처리·데이터 처리 생태계", "Java OpenCV 바인딩: 예제·자료 부족"),
    ("시뮬레이터", "Python paho-mqtt", "선정", "GW와 같은 토픽·JSON으로 B안 구현", "-"),
    ("배포", "Docker Compose (로컬·클라우드 VM 공통)", "선정", "5개 컨테이너를 한 번에 실행·재현", "쿠버네티스: 규모 대비 과함"),
    ("형상·CI", "Git, GitHub, GitHub Actions", "선정", "PR 리뷰, 빌드·테스트 자동화", "-"),
    ("테스트", "JUnit 5, Mockito, Vitest, k6", "선정", "단위·통합·성능 측정", "-"),
]

REPO = """todak/
├─ backend/                 Spring Boot (Gradle)
│  └─ src/main/java/kr/todak/
│     ├─ auth/  user/  farm/  sensor/  device/  control/
│     ├─ alert/ gdd/  weather/ image/  stream/  common/
│     └─ mqtt/                 MQTT 수신·발행 어댑터
├─ frontend/                React + TS (Vite)
│  └─ src/ pages/ components/ api/ hooks/ charts/
├─ simulator/               Python 가상 센서·장치 (B안)
├─ analyzer/                Python OpenCV 착색도 분석
├─ db/migration/            V1__schema.sql, V2__seed.sql (Flyway)
├─ infra/                   docker-compose.yml, mosquitto.conf
└─ docs/                    산출물, 테스트 로그, 스크린샷"""

# REQ → (설계 위치, 구현 모듈, API, 테스트)
TRACE = {
    "REQ-F-01": ("12장 수집 설계, 17장 DB", "mqtt, sensor", "API-26", "TC-001"),
    "REQ-F-02": ("14장 제어 로직", "control", "API-17", "TC-002"),
    "REQ-F-03": ("14장 제어 로직", "control", "API-17", "TC-003"),
    "REQ-F-04": ("14장 제어 로직", "control", "API-17", "TC-004"),
    "REQ-F-05": ("6장 범위", "sensor (확장)", "API-06", "-"),
    "REQ-F-06": ("4장·14장", "alert", "API-23", "TC-006"),
    "REQ-F-07": ("4장·16장", "analyzer, image", "API-24·25", "TC-007"),
    "REQ-F-08": ("15장 SD-02", "device, control", "API-12·14", "TC-008"),
    "REQ-F-09": ("14장 예외 처리", "alert", "API-18", "TC-009"),
    "REQ-F-10": ("16장 화면, 18장 API", "sensor, device", "API-09·10·15", "TC-010"),
    "REQ-F-11": ("4장 기준값, 17장 DB", "farm", "API-16", "TC-011"),
    "REQ-F-12": ("15장 권한", "auth, user", "API-01~04", "TC-012"),
    "REQ-F-13": ("13장 구역 설계", "farm, sensor", "API-05·08", "TC-013"),
    "REQ-F-14": ("5장 GDD 설계", "gdd", "API-19·20", "TC-014"),
    "REQ-F-15": ("3장 기후, 5장", "weather", "API-21·22", "TC-015"),
    "REQ-F-16": ("12장 명령 흐름", "control", "API-12·13", "TC-016"),
    "REQ-F-17": ("11장 B안", "simulator", "API-27", "TC-017"),
    "REQ-F-18": ("12장, 16장", "stream", "API-07", "TC-018"),
}

STUDENT_STEPS = [
    ("D1", "개발 환경·DB", "Docker Compose(MySQL·Mosquitto), Flyway V1·V2 적용, Spring Boot 골격", "스키마 20개 생성, 시드 입력 확인"),
    ("D2", "수집·시뮬레이터", "Python 시뮬레이터 11채널 송신, MQTT 수신·검증·저장", "TC-001, TC-017"),
    ("D3", "대시보드·SSE", "로그인, 구역 대시보드 카드, SSE 갱신", "TC-012, TC-018"),
    ("D4", "제어·명령", "규칙 엔진 CR-01~06, 명령 수명주기, 수동 모드", "TC-002~004, 008, 016"),
    ("D5", "경보", "임계·무응답·이상치·오프라인 경보, 중복 억제", "TC-009"),
    ("D6", "생육 분석", "기상 CSV 가져오기, 내부·외부 GDD 일 배치·그래프", "TC-014, 015"),
    ("D7", "이력·설정", "그래프·CSV, 기준값 버전, 구역·센서·장치 설정, 벌통 알림", "TC-006, 010, 011, 013"),
    ("D8", "확장·테스트", "착색도 분석(데이터 확보 시), 성능·보안 점검, 보고서 증빙 수집", "TC-007, TC-N03, TC-N04"),
]
