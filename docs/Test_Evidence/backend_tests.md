# 백엔드 시험 결과 (JUnit 5 · 실제 MySQL todak_test)

- 실행 시각: 2026-10-27 19:50 · 명령 `bash tools/run-backend-tests.sh` · HTML 보고서 `backend/build/reports/tests/test/index.html`
- 결과: **74건 중 통과 74, 실패 0, 미실행 0** · 소요 8.8초

| 클래스 | 시험 | 결과 | 초 |
|---|---|---|---|
| AccountIntegrationTest | 가입 검증: 약한 비밀번호·아이디 포함·확인 불일치·필수 약관 미동의·잘못된 아이디 400, 중복 409, 아이디 확인 API | ✅ 통과 | 0.493 |
| AccountIntegrationTest | 거절된 신청은 403 ACCOUNT_REJECTED | ✅ 통과 | 0.326 |
| AccountIntegrationTest | 관리자 임시 비밀번호 → 로그인 응답 mustChangePassword=true → 본인 변경(현재 비번 확인·규칙·다른 세션 폐기) → 플래그 해제 | ✅ 통과 | 0.789 |
| AccountIntegrationTest | 내 정보 조회·수정, 모든 기기 로그아웃 | ✅ 통과 | 0.126 |
| AccountIntegrationTest | 비밀번호 재설정 요청: 일치/불일치/없는 계정 모두 같은 응답, 일치할 때만 관리자 화면에 요청 표시 | ✅ 통과 | 0.022 |
| AccountIntegrationTest | 가입 신청은 PENDING → 로그인 403 ACCOUNT_PENDING → 관리자 승인(농장 지정) 후 로그인, 지정 농장만 접근 | ✅ 통과 | 0.376 |
| AnalyticsAndAdminIntegrationTest | TC-014 내부 GDD: 두 구역 센서 시간 평균 → 일평균 → GDD, 결측 20% 초과일은 불완전, 누적은 정식일부터 | ✅ 통과 | 0.161 |
| AnalyticsAndAdminIntegrationTest | TC-014 기준온도 변경은 이력이 남고 다음 계산에 반영된다 | ✅ 통과 | 0.141 |
| AnalyticsAndAdminIntegrationTest | TC-011 기준값 새 버전: 이전 버전 보존, 최소>최대 400 | ✅ 통과 | 0.106 |
| AnalyticsAndAdminIntegrationTest | TC-010 CSV 행 수 = DB 행 수, 데이터 출처 열 포함 | ✅ 통과 | 0.09 |
| AnalyticsAndAdminIntegrationTest | 관리자 센서 등록·수정, 규칙 히스테리시스 방향 검사 | ✅ 통과 | 0.119 |
| AnalyticsAndAdminIntegrationTest | 관리자 사용자 CRUD: 등록(BCrypt)·조회·수정·비활성화(세션 폐기)·농장 권한, 중복 아이디 409 | ✅ 통과 | 0.305 |
| AnalyticsAndAdminIntegrationTest | TC-015 기상자료개방포털 형식(CP949) CSV 가져오기 → 외부 GDD는 (최고+최저)/2, 결측 표시 | ✅ 통과 | 0.126 |
| AnalyticsAndAdminIntegrationTest | 엔티티 22개가 실제 테이블과 매핑된다 (모든 리포지토리 조회 성공) | ✅ 통과 | 0.034 |
| AuthIntegrationTest | 비활성 계정은 로그인 불가: 비밀번호가 맞으면 403 ACCOUNT_DISABLED, 틀리면 일반 401 | ✅ 통과 | 0.141 |
| AuthIntegrationTest | 비밀번호 해시는 BCrypt로 저장된다 | ✅ 통과 | 0.005 |
| AuthIntegrationTest | 로그인 성공: Access Token + HttpOnly·SameSite=Strict Refresh 쿠키 | ✅ 통과 | 0.076 |
| AuthIntegrationTest | 토큰 없음 401 UNAUTHORIZED, 위조 토큰 401 TOKEN_INVALID | ✅ 통과 | 0.01 |
| AuthIntegrationTest | 로그아웃하면 Refresh Token이 무효화된다 | ✅ 통과 | 0.08 |
| AuthIntegrationTest | 틀린 비밀번호 401(없는 아이디와 같은 메시지), 5번째 실패에 423 잠금, 잠금 중엔 맞는 비밀번호도 423 | ✅ 통과 | 0.353 |
| AuthIntegrationTest | Refresh: CSRF 헤더 없으면 403, 회전 후 이전 토큰 재사용 시 401 REFRESH_REUSED + 계열 폐기 | ✅ 통과 | 0.102 |
| AuthorizationIntegrationTest | 관리자 권한을 회수하면 농장 접근도 즉시 막힌다 | ✅ 통과 | 0.268 |
| AuthorizationIntegrationTest | 농가 농장 목록에는 자기 농장만 나온다 | ✅ 통과 | 0.085 |
| AuthorizationIntegrationTest | farmer01은 농장 2의 대시보드·센서·장치·알림에 접근 불가 | ✅ 통과 | 0.094 |
| AuthorizationIntegrationTest | 농가는 관리자 API 403 | ✅ 통과 | 0.081 |
| AuthorizationIntegrationTest | 관리자는 모든 농장 조회 가능 | ✅ 통과 | 0.101 |
| ControlIntegrationTest | TC-008·016 수동 명령: 확인 없으면 400, 202 SENT → ACK 후 ACKED·상태 반영, 같은 멱등키는 같은 명령 | ✅ 통과 | 0.117 |
| ControlIntegrationTest | TC-016 ACK 없음 → 1회 재전송 → TIMEOUT + DEVICE_NOACK 경보 (명령 전송 ≠ 장치 동작) | ✅ 통과 | 0.107 |
| ControlIntegrationTest | 수동 모드 장치는 자동 규칙이 건드리지 않지만 안전 한계(35℃)는 개입한다 | ✅ 통과 | 0.236 |
| ControlIntegrationTest | TC-002 고온 28℃ 이상 → 측창 OPEN 1회, 27℃(히스테리시스 구간) 유지, 26℃ 이하 → CLOSE | ✅ 통과 | 0.178 |
| ControlIntegrationTest | 최소 작동시간 안에는 반대 명령을 내지 않는다 | ✅ 통과 | 0.103 |
| ControlIntegrationTest | TC-004 관수: 배지수분 ≤55% → 밸브 ON, 일 최대 횟수 도달 시 차단 + 경보 | ✅ 통과 | 0.081 |
| ControlIntegrationTest | 기준값 이탈 경보는 30분 안 재발생 시 횟수만 늘고, 범위로 돌아오면 해결 | ✅ 통과 | 0.069 |
| ControlIntegrationTest | 게이트웨이 오프라인이면 수동 명령 503 | ✅ 통과 | 0.091 |
| DemoLoginIntegrationTest | 둘러보기: 사용 여부 공개 → VIEWER 토큰 발급 → 조회 200, 장치 제어·관리자 API 403 | ✅ 통과 | 0.063 |
| DemoLoginIntegrationTest | 둘러보기 계정이 VIEWER가 아니면(설정 실수) 거부한다 | ✅ 통과 | 0.014 |
| IngestIntegrationTest | 범위 밖 값은 OUT_RANGE로 저장되고 OUTLIER 경보가 열린다 | ✅ 통과 | 0.017 |
| IngestIntegrationTest | 통신 복구 재전송(buffered)도 저장되고 시간 집계에 반영된다 | ✅ 통과 | 0.067 |
| IngestIntegrationTest | 1분 사이 급변(spike_limit 초과)은 SPIKE | ✅ 통과 | 0.023 |
| IngestIntegrationTest | 같은 msgId·같은 분 재전송 100건 → 추가 저장 0건 | ✅ 통과 | 0.051 |
| IngestIntegrationTest | 형식 오류·미등록 센서는 거부 | ✅ 통과 | 0.011 |
| IngestIntegrationTest | MQTT 토픽으로 받은 값이 TB_SENSOR_DATA에 저장된다 | ✅ 통과 | 0.013 |
| PlanAlignmentIntegrationTest | REQ-F-15: 이미 있는 날짜는 409 DUPLICATE_DATES로 확인 요청, overwrite=true면 덮어쓴다 | ✅ 통과 | 0.178 |
| PlanAlignmentIntegrationTest | CR-01 2단계: 측창 개방 5분 뒤에도 30℃ 이상이면 환기팬 ON, 26℃ 이하면 이 규칙이 켠 환기팬 OFF | ✅ 통과 | 0.192 |
| PlanAlignmentIntegrationTest | CR-03 차광: 일사 800 이상이 10분 계속돼야 닫는다 (순간값 1건으로는 작동하지 않음) | ✅ 통과 | 0.06 |
| PlanAlignmentIntegrationTest | REQ-F-02 예외: 게이트웨이는 연결됐는데 온도 센서 값이 모두 없으면 CRITICAL 경보, 값이 오면 해결 | ✅ 통과 | 0.045 |
| PlanAlignmentIntegrationTest | REQ-F-13 구역: 등록, 중복 409, 센서·장치가 연결된 구역 삭제 409 ZONE_IN_USE, 빈 구역 삭제, 농가 403 | ✅ 통과 | 0.195 |
| PlanAlignmentIntegrationTest | REQ-F-09: 해결된 지 30분 안에 같은 경보가 다시 생기면 새 행을 만들지 않고 다시 연다 | ✅ 통과 | 0.02 |
| PlanAlignmentIntegrationTest | API-06 대시보드에 오늘 DLI·누적 GDD·최근 수집 시각, GDD 응답에 요약(경과일·결측·35℃/5℃ 일수) | ✅ 통과 | 0.113 |
| PlanAlignmentIntegrationTest | API-26 HTTP 대체 수집: 기기 토큰 없거나 틀리면 401, 정상 저장, 같은 msgId 재전송은 중복, 미등록 센서 거부 | ✅ 통과 | 0.103 |
| PlanAlignmentIntegrationTest | 표 39 CR-05: 한 구역(Z1)만 35℃를 넘어도 Z2 환기팬까지 모든 환기 장치를 연다 | ✅ 통과 | 0.076 |
| PlanAlignmentIntegrationTest | CR-06 저온 안전: 5℃ 이하면 난방 ON과 함께 열린 측창을 닫는다 (수동 모드여도) | ✅ 통과 | 0.051 |
| PlanAlignmentIntegrationTest | CR-04 관수 간격: 직전 자동 관수 후 30분 안에는 다시 열지 않는다 | ✅ 통과 | 0.065 |
| PlanAlignmentIntegrationTest | 표 41 VIEWER: 조회 200, 제어·모드·기준값·작기·알림 처리 403, 다른 농장·관리자 API 403 | ✅ 통과 | 0.109 |
| PlanAlignmentIntegrationTest | 13장 센서 고장 대응: Z1 배지수분 센서 값이 없으면 Z2 센서로 임시 대체해 관수, 둘 다 없으면 관수 안 함 | ✅ 통과 | 0.042 |
| PlanAlignmentIntegrationTest | 표 39 CR-05: 안전 한계 작동 시 CRITICAL 경보 / 표 67: 같은 Idempotency-Key 재요청은 기존 명령, 다른 본문은 409 | ✅ 통과 | 0.138 |
| GddCalculatorTest | 외부(최고+최저)/2 | ✅ 통과 | 0.0 |
| GddCalculatorTest | 기준온도 미만은 0 | ✅ 통과 | 0.0 |
| GddCalculatorTest | 유효 시간 80% 미만은 불완전, 0시간은 GDD 없음 | ✅ 통과 | 0.001 |
| GddCalculatorTest | 시간 평균 24개 → 일평균, 결측 없으면 complete | ✅ 통과 | 0.0 |
| GddCalculatorTest | 기준온도 이상: Tavg − Tbase | ✅ 통과 | 0.0 |
| GddCalculatorTest | 7일 누적이 손 계산과 일치 (오차 ≤ 0.1) | ✅ 통과 | 0.001 |
| GddCalculatorTest | 상한온도 초과분은 잘라낸다 | ✅ 통과 | 0.0 |
| JwtServiceTest | otherKeyRejected() | ✅ 통과 | 0.003 |
| JwtServiceTest | tamperedTokenRejected() | ✅ 통과 | 0.001 |
| JwtServiceTest | issueAndParse() | ✅ 통과 | 0.001 |
| JwtServiceTest | shortSecretRefused() | ✅ 통과 | 0.0 |
| JwtServiceTest | expiredRejected() | ✅ 통과 | 1.512 |
| RuleDecisionTest | deviceStates() | ✅ 통과 | 0.002 |
| RuleDecisionTest | unknownOperator() | ✅ 통과 | 0.001 |
| RuleDecisionTest | noChatterAroundThreshold() | ✅ 통과 | 0.0 |
| RuleDecisionTest | geHysteresis() | ✅ 통과 | 0.0 |
| RuleDecisionTest | leHysteresis() | ✅ 통과 | 0.001 |
| RuleDecisionTest | representativeIsConservative() | ✅ 통과 | 0.001 |
