# 요구사항 추적 매트릭스 (RTM) — TODAK v1.1

요구사항 ID → 화면 ID → API → Service → DB 테이블 → 소스 파일 → 시험 ID → 실행 증빙 → 완료 보고서

- 소스 경로: 백엔드 `backend/src/main/java/kr/todak/…`, 프런트 `frontend/src/…`, 시뮬레이터 `simulator/todak_sim/…`
- 시험 ID: `JU-클래스` = JUnit(백엔드), `FE-` = Vitest, `SIM-` = pytest, `E2E-nn` = Playwright, `SC-` = 시나리오 시험, `PF-` = k6
- 증빙: `docs/Test_Evidence/` 아래 파일 (`screenshots/*.png`, `e2e_results.md`, `scenario_results.md`, `performance.md`, `backend_tests.md`)
- 완료 보고서: `04_시스템_개발_완료보고서` 4장 '요구사항 완료 현황'의 같은 ID 행
- 상태: ✅ 완료(시뮬레이터 검증) · ⏸ 확장/미구현 · 📏 운영 측정 필요

| 요구사항 | 화면 | API | Service | DB 테이블 | 소스 | 시험 | 증빙 | 상태 |
|---|---|---|---|---|---|---|---|---|
| REQ-F-01 환경 데이터 수집 | SCR-02, A3, A5 | MQTT sensor 토픽, POST /api/ingest/sensor-data, GET /api/admin/logs/ingest | SensorIngestService, HttpIngestController, HourlyAggregator | TB_SENSOR_DATA, TB_SENSOR_DATA_HOURLY, TB_SENSOR | ingest/*, mqtt/*, analytics/HourlyAggregator.java, simulator/todak_sim/gateway.py | JU-IngestIntegrationTest(6), JU-PlanAlignment(httpIngest), SIM-test_model | backend_tests.md, 07c_admin_logs_ingest.png, performance.md(저장률) | ✅ |
| REQ-F-02 온도 자동 제어 | SCR-04, SCR-07 | (규칙 엔진) GET /api/controls/rules | RuleEngine, RuleDecision, CommandService | TB_CONTROL_RULE, TB_CONTROL_COMMAND, TB_CONTROL_LOG | control/RuleEngine.java, RuleDecision.java | JU-RuleDecisionTest, JU-Control(TC-002, 최소 작동, 수동·안전), JU-PlanAlignment(CR-01 2단계, CR-06, 센서 모두 이상), SC-고온, SC-저온 | scenario_results.md, 10d_farmer_control.png | ✅ |
| REQ-F-03 광 제어 | SCR-04, SCR-03 | GET /api/analytics/daily (DLI) | RuleEngine(CR-03·07, 스케줄 모드), AnalyticsService | TB_CONTROL_RULE, TB_SENSOR_DATA_HOURLY | control/RuleEngine.java, analytics/AnalyticsService.java | JU-PlanAlignment(CR-03 10분 지속) | 10h_farmer_growth_gdd.png | ✅ |
| REQ-F-04 관수·양액 | SCR-04 | (규칙 엔진) | RuleEngine(CR-04), ThresholdEvaluator(EC·pH) | TB_CONTROL_RULE, TB_CONTROL_COMMAND, TB_ALERT | control/RuleEngine.java, ThresholdEvaluator.java | JU-Control(TC-004 일 상한), JU-PlanAlignment(CR-04 간격, 구역 대체), SC-관수 부족 | scenario_results.md | ✅ |
| REQ-F-05 육묘 모니터링 | - | - | - | (TB_ZONE로 확장 가능) | - | - | - | ⏸ 확장 |
| REQ-F-06 수정 지원 알림 | SCR-08(재배 관리), SCR-06 | GET·POST /api/beehives | MonitoringJobs.beehives, ThresholdEvaluator(개화기) | TB_BEEHIVE, TB_ALERT | alert/MonitoringJobs.java, control/ThresholdEvaluator.java, pages/farmer/Crop.tsx | (시드 벌통 D-1 경보 수동 확인) | 10g_farmer_standards.png, 10f_farmer_alerts.png | ✅ |
| REQ-F-07 수확 판별 | SCR-09 | (API-24·25 없음) | - | TB_IMAGE_RESULT | - | - | 10i_farmer_harvest.png('확장 기능 · 이번 버전 미구현' 안내) | ⏸ 확장 |
| REQ-F-08 원격 제어·모드 | SCR-04 | POST /api/devices/{id}/commands, PATCH /api/devices/{id}/mode | CommandService, DeviceController | TB_CONTROL_COMMAND, TB_DEVICE, TB_SETTING_HISTORY | web/DeviceController.java, pages/farmer/Control.tsx | JU-Control(TC-008·016), PF-control_ack, E2E-10, E2E-12 | 10d_farmer_control.png, performance.md | ✅ |
| REQ-F-09 이상 감지·경보 | SCR-06, SCR-02 | GET·PATCH /api/alerts | AlertService, ThresholdEvaluator, MonitoringJobs, GatewayService | TB_ALERT, TB_ALERT_DELIVERY | alert/*, control/ThresholdEvaluator.java | JU-Control(30분 억제), JU-PlanAlignment(해결 후 30분 재오픈), JU-Ingest(OUTLIER), SC-센서 무응답, SC-통신 단절 | 10f_farmer_alerts.png, scenario_results.md | ✅ (SMS ⏸) |
| REQ-F-10 이력·그래프·CSV | SCR-03, SCR-05 | GET /api/sensor-data/series, /export.csv, GET /api/controls/commands·logs | SensorDataController, AnalyticsService | TB_SENSOR_DATA(_HOURLY), TB_CONTROL_LOG | web/SensorDataController.java, pages/farmer/Analytics.tsx | JU-Analytics(TC-010 CSV 행 수), PF-series7d | 10h_farmer_growth_gdd.png, performance.md | ✅ |
| REQ-F-11 재배 기준값 | SCR-07, SCR-08 | GET·POST /api/crop-standards, PATCH /api/admin/rules/{id} | CropController, GatewayService.publishConfig | TB_CROP_STD, TB_CONTROL_RULE, TB_SETTING_HISTORY | web/CropController.java, components/StdForm.tsx | JU-Analytics(TC-011), JU-Admin(규칙 방향 검사) | 07b_admin_standards_rules.png, 10g_farmer_standards.png | ✅ |
| REQ-F-12 사용자·권한 | SCR-01, 01a~c, A2, 내 정보 | /api/auth/**, /api/admin/users/** | AuthService, JwtService, PasswordPolicy, FarmAccess, SecurityConfig | TB_USER, TB_USER_FARM, TB_REFRESH_TOKEN | auth/*, common/FarmAccess.java, config/SecurityConfig.java, pages/auth/*, pages/admin/Users.tsx | JU-Auth(7), JU-Authorization(5), JU-Account(6), JU-PlanAlignment(VIEWER), JU-JwtServiceTest, FE-password·login, E2E-01~06, 09, 11~14 | e2e_results.md, 01~06·11~14 *.png | ✅ |
| REQ-F-13 관리 구역 | SCR-10(A3) | GET /api/farms/{id}/zones, POST·DELETE /api/admin/zones | AdminController | TB_ZONE, TB_SENSOR, TB_DEVICE | admin/AdminController.java, pages/admin/Equipment.tsx | JU-PlanAlignment(zones), E2E-07 | 07a_admin_equipment.png | ✅ |
| REQ-F-14 GDD 분석 | SCR-08(분석) | GET /api/analytics/gdd, /gdd/export.csv, PATCH /api/crop-cycles/{id} | GddCalculator, AnalyticsService | TB_GDD_DAILY, TB_CROP_CYCLE, TB_SENSOR_DATA_HOURLY | analytics/GddCalculator.java, AnalyticsService.java | JU-GddCalculatorTest(7, 손 계산 7일 오차 ≤ 0.1), JU-Analytics(TC-014 ×2) | 10h_farmer_growth_gdd.png | ✅ |
| REQ-F-15 외부 기상 자료 | A6, 분석 | POST /api/admin/weather/import, GET /api/admin/weather, GET /api/analytics/weather | WeatherImportService | TB_WEATHER_DAILY | analytics/WeatherImportService.java, pages/admin/Weather.tsx | JU-Analytics(TC-015 CP949), JU-PlanAlignment(덮어쓰기 확인) | 07f_admin_weather.png | ✅ (양평 202 실측 2026-10-01~26, `docs/Test_Evidence/kma/`) |
| REQ-F-16 명령 상태 추적 | SCR-04, A5 | GET /api/controls/commands/{id} | CommandService.checkTimeouts | TB_CONTROL_COMMAND | control/CommandService.java | JU-Control(TC-016 재전송·TIMEOUT), JU-PlanAlignment(409 DUPLICATE_REQUEST), SC-장치 오류 | 07d_admin_logs_commands.png, scenario_results.md | ✅ |
| REQ-F-17 시뮬레이터 | A1 | POST /api/admin/simulator/scenario, MQTT sim/scenario | (Python) Greenhouse, VirtualGateway | - | simulator/todak_sim/*.py | SIM-test_model(5), SC-전체 6구간 | scenario_results.md, 05_admin_dashboard.png | ✅ |
| REQ-F-18 실시간 갱신 | SCR-02, SCR-04 | GET /api/stream (SSE) | SseHub | - | stream/SseHub.java, hooks/useApi.ts | E2E-10(대시보드 '실시간 연결' 표시) | 10a_farmer_dashboard.png | ✅ (3초 지연 미측정) |
| REQ-N-01 성능 | - | 조회·제어 API | - | - | tools/perf/k6_api.js | PF-series7d, PF-dashboard, PF-control_ack | performance.md | ✅/📏 |
| REQ-N-02 가용성 | - | - | - | - | docker-compose.yml(restart) | - | - | 📏 운영 1개월 |
| REQ-N-03 안전성 | - | MQTT LWT, config | GatewayService, 시뮬레이터 FAILSAFE·버퍼 | TB_GATEWAY | control/GatewayService.java, simulator/todak_sim/gateway.py | JU-Ingest(buffered 재전송), SC-통신 단절 | scenario_results.md | ✅ |
| REQ-N-04 보안 | SCR-01 | /api/auth/** | AuthService, SecurityConfig | TB_USER, TB_REFRESH_TOKEN | auth/*, infra/mosquitto/acl | JU-Auth, JU-Authorization, JU-Account | backend_tests.md | ✅ (HTTPS·TLS ⏸) |
| REQ-N-05 데이터 보존 | - | - | RetentionJob, HourlyAggregator | TB_SENSOR_DATA(_HOURLY) | alert/RetentionJob.java, tools/backup-db.sh | (코드 검토) | - | ✅ (백업 cron은 운영자) |
| REQ-N-06 사용성 | 전체 | - | - | - | tailwind.config.js, components/ui.tsx | E2E 전체 | screenshots/*.png | ✅ (사용성 테스트 📏) |
| REQ-N-07 반응형 | 전체 | - | - | - | components/Layout.tsx | E2E-15 (360px 가로 스크롤 0) | 15a~c_mobile_*.png | ✅ (Edge·Safari 📏) |
