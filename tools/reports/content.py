# -*- coding: utf-8 -*-
"""개발·완료 보고서 공통 내용. 수치는 evidence.py가 증빙 파일에서 읽고, 여기에는 사실 서술만 둔다."""

# 요구사항 완료 현황 (검토서·RTM과 같은 판정)
REQ_STATUS = [
    ("REQ-F-01", "환경 데이터 수집", "완료", "MQTT·HTTP 대체 수집, 검증·중복 제거·품질 플래그", "JU-Ingest 6, PlanAlignment(httpIngest)"),
    ("REQ-F-02", "온도 자동 제어", "완료", "CR-01(2단계)·02·05·06, 센서 대체·모두 이상 시 중지 경보", "JU-Control, PlanAlignment, 시나리오 고온·저온"),
    ("REQ-F-03", "광 제어", "완료", "CR-03 10분 지속·시간당 2회, CR-07 보광, DLI, 일사 이상 시 스케줄", "PlanAlignment(CR-03)"),
    ("REQ-F-04", "관수·양액 관리", "완료", "CR-04 1회 5분·일 12회·간격 30분, EC·pH 경보", "JU-Control TC-004, 시나리오 관수 부족"),
    ("REQ-F-05", "육묘 환경 모니터링", "미구현(확장)", "계획서 9.4 확장 범위", "-"),
    ("REQ-F-06", "수정 지원 알림", "완료", "벌통 교체 D-1, 개화기 고온·다습 경고", "화면 확인"),
    ("REQ-F-07", "수확 적기 판단", "미구현(확장)", "카메라·OpenCV, 라벨 이미지 필요", "-"),
    ("REQ-F-08", "원격 제어·모드 전환", "완료", "확인 절차, 수동 유지, 안전 한계 우선(423)", "JU-Control TC-008, k6, E2E-10·12"),
    ("REQ-F-09", "이상 감지·경보", "완료(SMS 확장)", "7종 경보, 30분 중복 억제", "JU-Control, PlanAlignment, 시나리오"),
    ("REQ-F-10", "이력·그래프·CSV", "완료", "지표·집계 선택, 원시 90일, CSV", "TC-010, k6"),
    ("REQ-F-11", "재배 기준값 관리", "완료", "버전 관리, 범위 역전 거부, GW 동기화, 농가 등록", "TC-011"),
    ("REQ-F-12", "사용자·권한 관리", "완료", "ADMIN·FARMER·VIEWER, 가입 승인, 잠금, 비밀번호 정책", "JU-Auth·Authorization·Account, E2E"),
    ("REQ-F-13", "관리 구역 관리", "완료", "구역 등록, 매핑 장비 있으면 삭제 거부", "PlanAlignment(zones)"),
    ("REQ-F-14", "GDD 분석", "완료", "내부·외부 분리, 불완전 표시, 기준·상한 변경 이력", "GddCalculatorTest 7, TC-014"),
    ("REQ-F-15", "외부 기상 자료", "완료(실자료 미입력)", "ASOS CSV(CP949·UTF-8), 덮어쓰기 확인", "TC-015, PlanAlignment"),
    ("REQ-F-16", "제어 명령 상태 추적", "완료", "요청·전송·실행 확인·실패·응답 없음, 1회 재전송", "TC-016, 시나리오 장치 오류"),
    ("REQ-F-17", "가상 센서·장치 시뮬레이터", "완료", "열 모델, 시나리오 9종, 백필", "pytest 5, 시나리오 시험"),
    ("REQ-F-18", "실시간 대시보드 갱신", "완료", "SSE, 15초 재연결", "E2E-10"),
    ("REQ-N-01", "성능", "측정 완료", "k6 (조회 p95, 제어 ACK p95)", "performance.md"),
    ("REQ-N-02", "가용성 99.5%", "측정 불가", "운영 1개월 필요", "-"),
    ("REQ-N-03", "안전성(단절 시 안전 운전)", "완료", "LWT·FAILSAFE·버퍼 재전송", "시나리오 통신 단절"),
    ("REQ-N-04", "보안", "완료(HTTPS 배포 시)", "BCrypt, JWT 15분+Refresh 회전, 역할·농장 인가, MQTT ACL", "JU-Auth·Authorization·Account"),
    ("REQ-N-05", "데이터 보존", "완료", "원시 3년 삭제 배치, 집계 영구, 백업 스크립트", "코드 검토"),
    ("REQ-N-06", "사용성", "완료(사용성 시험 미실시)", "본문 16px, 대비 4.5:1 이상, 3단계 이내", "E2E"),
    ("REQ-N-07", "반응형", "완료(Chromium)", "360~1920px", "E2E-15"),
]

# 개발 중 생긴 문제와 해결 (실제 겪은 일)
PROBLEMS = [
    ("MySQL 초기화 스크립트 실행 오류", "init 폴더의 .sh가 'bad interpreter'로 실패", "SQL 파일(01-test-db.sql)로 바꿔 시험용 DB를 만듦"),
    ("빈(bean) 순환 의존", "MQTT 게이트웨이 ↔ 메시지 라우터 ↔ 명령 서비스가 서로를 참조", "라우터를 @Lazy로 지연 주입"),
    ("테이블 이름 대소문자", "JPA가 TB_GATEWAY를 tb_gateway로 바꿔 찾지 못함", "PhysicalNamingStrategyStandardImpl로 이름 그대로 사용"),
    ("시간 집계 SQL 오류", "only_full_group_by 모드에서 별칭 충돌", "집계 SQL을 파생 테이블 별칭(t.hr)으로 다시 작성"),
    ("백필 때 메시지 유실·지연", "14일치 2만여 건을 한꺼번에 보내 브로커 큐가 넘침", "브로커 큐 한도 상향, 센서 캐시·INSERT IGNORE 한 번 쿼리, 영구 세션"),
    ("ACK가 SENT보다 먼저 도착", "빠른 가상 장치의 ACK가 상태 저장 전에 와서 덮어씀", "SENT를 먼저 저장한 뒤 발행, 트랜잭션 범위 축소"),
    ("개발 PC 절전 후 MQTT 재연결 반복", "밀린 메시지를 Paho 수신 스레드에서 DB 처리 → keepalive 응답 못 함, connectComplete 안 동기 구독 교착", "수신 처리를 별도 단일 스레드로, 구독은 제어 스레드로 분리"),
    ("계획서와 불일치 발견", "VIEWER·구역 등록·규칙 세부 조건·본문 16px 등 누락", "검토서 작성 후 V3 마이그레이션·코드 보완, 통합 시험 13건 추가"),
    ("시나리오가 시연에 너무 느림", "야간 고온 시나리오가 35℃까지 1시간 이상", "고온·관수 부족 시나리오 강도 조정 (시뮬레이터 모델)"),
    ("E2E 시험이 멈춤", "SSE 연결 때문에 'network idle'이 끝나지 않음", "화면 내용·차트가 나타날 때까지 기다리도록 변경"),
    ("시험 입력값이 급변 필터에 걸림", "31→25.5℃ 한 번에 바뀌어 SPIKE로 판정, 제어 판단에서 제외", "엔진은 정상 — 시험값을 급변 한계 안(26℃)으로 수정"),
]

PROJECT_TREE = """TODAK-SmartFarm/
├── backend/                Spring Boot 3.3 (Java 21, Gradle)
│   └── src/main/java/kr/todak/
│       ├── auth/           로그인·회원가입·JWT·Refresh 회전·비밀번호 정책
│       ├── admin/          관리자 API (사용자 승인·구역·센서·장치·규칙·로그·기상·시나리오)
│       ├── web/            농가 API (농장·센서 데이터·장치·알림·재배·분석)
│       ├── ingest/         센서 수집 (MQTT·HTTP 대체)
│       ├── control/        규칙 엔진·명령 수명주기·게이트웨이·기준 이탈
│       ├── analytics/      GDD·시간 집계·일별 통계·기상 CSV
│       ├── alert/          경보·감시 작업·보존 배치
│       ├── mqtt/ stream/   MQTT 어댑터, SSE
│       └── domain/ repo/   JPA 엔티티 22개·리포지토리
│   └── src/main/resources/db/migration/  V1 스키마, V2 시드, V3 계획서 정합
├── frontend/               React 18 + TS + Tailwind (nginx로 배포)
│   └── src/pages/{auth,farmer,admin}, components, hooks, api
├── simulator/              Python 가상 센서·장치 (GW-01 역할)
├── infra/                  mosquitto 설정·ACL, MySQL 초기화
├── tools/                  시험·증빙·성능·보고서 스크립트
├── docs/                   검토서·RTM·다이어그램·시험 증빙
└── docker-compose.yml, .env.example, README.md"""

SCREENS = [
    ("01_login", "SCR-01 로그인", "REQ-F-12", "아이디 저장·비밀번호 보기·가입 링크"),
    ("02_login_error", "SCR-01 로그인 실패 안내", "REQ-F-12", "없는 아이디와 같은 문구로 계정 존재를 숨김"),
    ("03c_signup_form", "회원가입 2단계 정보 입력", "REQ-F-12", "아이디 중복·비밀번호 규칙 실시간 검사"),
    ("03d_signup_done", "회원가입 신청 완료", "REQ-F-12", "관리자 승인 절차 안내"),
    ("04_login_pending", "승인 전 로그인", "REQ-F-12", "승인 대기 안내"),
    ("05_admin_dashboard", "SCR-A1 관리자 대시보드", "REQ-F-17", "센서·장치·수집·경보·명령 요약, 시나리오 실행"),
    ("06a_admin_users_pending", "SCR-A2 가입 승인 대기", "REQ-F-12", "신청 메모·승인·거절"),
    ("06b_admin_approve_modal", "SCR-A2 승인 (역할·농장 지정)", "REQ-F-12", "농장 1개 이상 지정해야 승인"),
    ("07a_admin_equipment", "SCR-A3 센서·장치·구역", "REQ-F-13", "구역 등록·삭제 거부, 수신률, 기기 토큰"),
    ("07b_admin_standards_rules", "SCR-07 기준값·규칙", "REQ-F-11", "버전 이력, 규칙 세부 조건"),
    ("07d_admin_logs_commands", "SCR-A5 제어 명령 로그", "REQ-F-16", "전송·실행 확인 구분"),
    ("10a_farmer_dashboard", "SCR-02 농가 대시보드", "REQ-F-01, F-18", "최신값·DLI·누적 GDD·24시간 그래프·장치·알림"),
    ("10c_farmer_graph", "SCR-03 환경 그래프", "REQ-F-10", "기간·지표·집계 선택, 일별 통계·DLI, CSV"),
    ("10h_farmer_growth_gdd", "SCR-08 생육 분석 (GDD·기상)", "REQ-F-14, F-15", "내부·외부 GDD, 결측·불완전, 정식일·기준 온도, 벌통"),
    ("10d_farmer_control", "SCR-04 장치 제어", "REQ-F-08, F-16", "수동 제어·모드·유지 시간·명령 상태"),
    ("10e_farmer_history", "SCR-05 제어 이력", "REQ-F-10, F-16", "장치·출처·기간 필터, 명령과 실제 상태 변경 구분"),
    ("10g_farmer_standards", "SCR-07 재배 기준값·제어 규칙", "REQ-F-11", "단계별 기준 버전, 새 버전 등록, 규칙 임계값"),
    ("10i_farmer_harvest", "SCR-09 수확 판별", "REQ-F-07", "확장 기능 미구현 안내 (가짜 결과 없음)"),
    ("10f_farmer_alerts", "SCR-06 알림 센터", "REQ-F-09", "기준 이탈·센서 무응답·통신 장애 경보, 심각도·상태 필터, 확인·해결"),
    ("12_viewer_control_readonly", "조회 전용 계정 제어 화면", "REQ-F-12", "버튼 비활성 + 서버 403"),
    ("13_password_change_required", "임시 비밀번호 첫 로그인", "REQ-F-12", "새 비밀번호로 바꾸기 전 이동 불가"),
    ("15b_mobile_dashboard", "모바일 360px 대시보드", "REQ-N-07", "가로 스크롤 없음"),
    ("08_swagger", "Swagger API 문서", "REQ-N-04", "인증 후 API 실행"),
    ("16_mysql_query", "MySQL 실제 조회 결과", "REQ-F-01", "mysql CLI 출력 그대로"),
    ("17_backend_test_report", "백엔드 테스트 보고서", "-", "Gradle JUnit HTML 보고서"),
]

NOT_DONE = [
    ("REQ-F-05 육묘 모니터링", "계획서 확장 범위", "구역 등록으로 육묘 구역을 만들면 같은 화면 사용 가능"),
    ("REQ-F-07 수확 판별 (API-24·25, SCR-09)", "라벨 이미지 300장 이상 필요, 확장 범위", "카메라 설치·데이터 수집 후 OpenCV 분석 서비스"),
    ("SMS·이메일 알림", "유료 발송 서비스 필요, 확장 범위", "현재는 웹 알림 + 관리자 초기화 요청 방식"),
    ("HTTPS·MQTT TLS", "로컬 실행 환경", "운영 서버 배포 시 인증서 적용, COOKIE_SECURE=true"),
    ("실제 기상청 ASOS 자료", "아직 내려받아 가져오지 않음", "기상자료개방포털에서 양평(202) 일자료 CSV 업로드"),
    ("실장비(A안) 연결", "센서·장비 미확보, 전기 안전 검증 필요", "Modbus 게이트웨이 연동 후 '알림만' 모드 1주 시범"),
    ("가용성 99.5%·농가 사용성 시험", "운영 기간·실사용자 필요", "시범 운영 단계에서 측정"),
    ("Edge·Safari 실기기 확인", "E2E는 Chromium만", "브라우저 매트릭스 시험"),
]


# 지시서 14절 '필수 증빙 12종' (화면명·화면 ID·요구사항·구현 기능·작동 설명·데이터·시험)
EVIDENCE12 = [
    ("01_login", "로그인", "SCR-01", "REQ-F-12", "아이디·비밀번호 로그인, 아이디 저장, 5회 실패 잠금 안내", "로그인 성공 시 역할별 첫 화면으로 이동, 실패 시 계정 존재를 숨긴 같은 문구", "시드 시험 계정", "E2E-01·02 통과"),
    ("05_admin_dashboard", "관리자 메인 대시보드", "SCR-A1", "REQ-F-17", "센서·장치·수집·경보·명령 요약, 게이트웨이 상태, 시나리오 실행", "30초마다 API로 갱신, 시나리오 버튼은 MQTT로 시뮬레이터에 전달", "시뮬레이션", "E2E-05 통과"),
    ("10a_farmer_dashboard", "농가 메인 대시보드", "SCR-02", "REQ-F-01, F-18", "최신값 카드·구역 탭·DLI·누적 GDD·24시간 그래프·장치·알림", "SSE로 새 측정값이 오면 카드가 바로 바뀜", "시뮬레이션", "E2E-10 통과"),
    ("06a_admin_users_pending", "관리자 사용자 관리", "SCR-A2 (SCR-10)", "REQ-F-12", "가입 승인·거절, 역할·농장 권한, 임시 비밀번호, 잠금 해제", "승인 전 로그인 차단, 승인 시 지정 농장만 접근", "시험 계정", "E2E-06 통과"),
    ("07a_admin_equipment", "센서·장치·구역 관리", "SCR-A3 (SCR-10)", "REQ-F-13", "센서 등록·위치·상태·수신률, 장치, 구역 등록·삭제, 기기 토큰", "센서·장치가 연결된 구역 삭제는 409로 거부", "시드 + 시뮬레이션", "E2E-07 통과"),
    ("10c_farmer_graph", "환경 데이터 그래프", "SCR-03", "REQ-F-10", "기간·지표·집계(1분/시간) 선택, 일별 통계·일교차·DIF·DLI, CSV", "MySQL 시간 집계·원시 데이터를 API로 조회해 그림", "시뮬레이션", "E2E-10 통과"),
    ("10h_farmer_growth_gdd", "적산온도(GDD) 분석", "SCR-08", "REQ-F-14, F-15", "내부·외부 GDD 분리, 결측·불완전 표시, 기준·상한 온도 변경", "GDD = max(0, min(평균, 상한) − 기준), 손 계산과 오차 ≤ 0.1", "시뮬레이션 (기상청 자료 미입력)", "E2E-10·GddCalculatorTest 통과"),
    ("10d_farmer_control", "자동·수동 제어", "SCR-04", "REQ-F-02~04, F-08, F-16", "장치별 켜기·끄기, 자동/수동 전환, 수동 유지 시간, 명령 상태", "명령 전송(SENT)과 실행 확인(ACKED)을 구분해 표시", "가상 장치", "E2E-10·시나리오 6/6 통과"),
    ("10f_farmer_alerts", "알림", "SCR-06", "REQ-F-09", "경보 목록, 심각도·상태 필터, 확인·해결", "같은 문제는 30분 안 재발생 시 횟수만 늘어남", "시뮬레이션", "E2E-10·시나리오 통과"),
    ("16_mysql_query", "MySQL 데이터 조회", "-", "REQ-F-01", "테이블·마이그레이션·사용자·수집·명령 조회", "mysql CLI 실제 출력을 그대로 화면으로 만든 것", "실제 DB 내용", "collect_evidence.py"),
    ("08_swagger", "Swagger API 실행", "-", "REQ-N-04", "API 문서, Authorize 후 실행", "요구사항 ID·테이블·오류 코드 표기", "-", "E2E-08 통과"),
    ("17_backend_test_report", "테스트 실행 결과", "-", "-", "Gradle JUnit 보고서", "실제 MySQL에 붙인 단위·통합 시험", "-", "백엔드 72/72 통과"),
]

# 개발 계획서 v2.0과 실제 구현이 달라진 점 (검토서 docs/Development_Plan/계획서_대비_구현_검토.md 요약)
PLAN_CHANGES = [
    ("API 경로", "/api/v1/…", "/api/… (auth·admin·farms·sensors·sensor-data·devices·controls·alerts·crop-standards·analytics)", "후속 개발 지시서의 API 묶음에 맞춤"),
    ("Access Token", "JWT 1시간", "JWT 15분 + Refresh Token 회전(HttpOnly 쿠키)", "더 강한 보안 (후속 지시서)"),
    ("DB 테이블", "20개", "22개 (+TB_USER_FARM, TB_REFRESH_TOKEN), V3에서 컬럼 20개 추가", "농장별 권한·토큰 회전·가입 승인·규칙 세부 조건"),
    ("자동 제어 규칙", "CR-01~06", "CR-01~07 (CR-07 보광 추가)", "REQ-F-03 보광을 규칙으로 구현"),
    ("관수 해제", "시간 종료(최대 5분)", "배지수분 65% 또는 5분 중 먼저", "과습 방지"),
    ("프런트 UI", "MUI", "Tailwind CSS", "후속 지시서 지정"),
    ("백엔드·IoT", "Java 17, Spring Integration MQTT", "Java 21, Eclipse Paho", "최신 LTS, 의존성 단순화"),
    ("화면", "SCR-01~10", "SCR-01~10 + 회원가입·내 정보·관리자 화면 6개, SCR-09는 확장 안내", "사용자 요청·후속 지시서"),
    ("목록 응답", "{content, page, size, total}", "size 파라미터가 있는 배열", "화면이 최근 N건만 사용"),
    ("미구현", "-", "F-05 육묘, F-07 수확 판별(API-24·25), SMS, HTTPS 배포", "계획서상 확장 범위·운영 단계"),
]
