-- TODAK V3: 개발 계획서 v2.0 대비 검토(docs/Development_Plan/계획서_대비_구현_검토.md)에서 찾은 차이를 메운다.
--  1) 회원가입·승인·비밀번호 재설정 요청·최초 로그인 비밀번호 변경 [REQ-F-12]
--  2) 자동 제어 규칙 표 39의 세부 조건: 지속 시간(CR-03), 시간당 횟수(CR-03), 관수 간격(CR-04),
--     2단계 환기팬(CR-01), 저온 안전 시 측창 닫기(CR-06) [REQ-F-02~04]
--  3) 게이트웨이 기기 토큰 — MQTT 장애 시 HTTP 대체 수집(API-26) [REQ-F-01]
--  4) VIEWER(검수자, 조회 전용) 테스트 계정 [표 41]

ALTER TABLE TB_USER
  ADD COLUMN approval_status VARCHAR(10) NOT NULL DEFAULT 'APPROVED' COMMENT 'PENDING(가입 신청) / APPROVED / REJECTED' AFTER is_active,
  ADD COLUMN requested_role  VARCHAR(10)  NULL COMMENT '가입 시 요청 역할 (FARMER/VIEWER)' AFTER approval_status,
  ADD COLUMN signup_note     VARCHAR(300) NULL COMMENT '가입 신청 메모: 농장 위치·이름 등' AFTER requested_role,
  ADD COLUMN approved_by     INT          NULL AFTER signup_note,
  ADD COLUMN approved_at     DATETIME     NULL AFTER approved_by,
  ADD COLUMN must_change_pw  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 = 다음 로그인 때 비밀번호 변경 필요(관리자 초기화 후)' AFTER approved_at,
  ADD COLUMN pw_changed_at   DATETIME     NULL AFTER must_change_pw,
  ADD COLUMN pw_reset_requested_at DATETIME NULL COMMENT '비밀번호 재설정 요청 시각(관리자가 처리)' AFTER pw_changed_at,
  ADD COLUMN terms_agreed_at   DATETIME   NULL COMMENT '이용약관 동의(필수)' AFTER pw_reset_requested_at,
  ADD COLUMN privacy_agreed_at DATETIME   NULL COMMENT '개인정보 수집·이용 동의(필수)' AFTER terms_agreed_at,
  ADD COLUMN notify_agreed     TINYINT(1) NOT NULL DEFAULT 0 COMMENT '알림 수신 동의(선택)' AFTER privacy_agreed_at,
  ADD COLUMN last_login_at   DATETIME     NULL AFTER notify_agreed,
  ADD CONSTRAINT ck_user_approval CHECK (approval_status IN ('PENDING','APPROVED','REJECTED')),
  ADD CONSTRAINT fk_user_approved_by FOREIGN KEY (approved_by) REFERENCES TB_USER(user_id),
  ADD INDEX ix_user_approval (approval_status);

ALTER TABLE TB_CONTROL_RULE
  ADD COLUMN sustain_sec        INT           NULL COMMENT '조건이 이 시간 동안 계속돼야 작동·해제 (CR-03 10분)' AFTER max_daily_count,
  ADD COLUMN max_per_hour       INT           NULL COMMENT '장치별 1시간 최대 작동 횟수 (CR-03 2회)' AFTER sustain_sec,
  ADD COLUMN min_interval_sec   INT           NULL COMMENT '작동 사이 최소 간격 (CR-04 관수 30분)' AFTER max_per_hour,
  ADD COLUMN stage2_device_type VARCHAR(20)   NULL COMMENT '2단계 장치 유형 (CR-01 환기팬)' AFTER min_interval_sec,
  ADD COLUMN stage2_threshold   DECIMAL(10,3) NULL COMMENT '2단계 작동값 (CR-01 30℃)' AFTER stage2_device_type,
  ADD COLUMN stage2_delay_sec   INT           NULL COMMENT '1단계 작동 후 대기 (CR-01 5분)' AFTER stage2_threshold,
  ADD COLUMN also_close_type    VARCHAR(20)   NULL COMMENT '작동 시 함께 닫을 장치 유형 (CR-06 측창)' AFTER stage2_delay_sec;

ALTER TABLE TB_GATEWAY
  ADD COLUMN device_token_hash CHAR(64) NULL COMMENT 'HTTP 대체 수집용 기기 토큰의 SHA-256 (원문은 발급 때 한 번만 표시)' AFTER synced_std_version;

-- 표 39 세부 조건 반영
UPDATE TB_CONTROL_RULE SET target_device_type = 'VENT', stage2_device_type = 'FAN', stage2_threshold = 30.0, stage2_delay_sec = 300
 WHERE rule_code = 'CR-01';
UPDATE TB_CONTROL_RULE SET sustain_sec = 600, max_per_hour = 2 WHERE rule_code = 'CR-03';
UPDATE TB_CONTROL_RULE SET min_interval_sec = 1800 WHERE rule_code = 'CR-04';
UPDATE TB_CONTROL_RULE SET also_close_type = 'VENT' WHERE rule_code = 'CR-06';

-- 검수자(VIEWER) 테스트 계정 — 비밀번호는 README '테스트 계정' 절
INSERT INTO TB_USER (user_id, login_id, password_hash, name, phone, role) VALUES
  (4, 'viewer01', '$2b$10$Ez2HrhlYQfBCrGCzSwMbUOiIHnXbl18qCulZ0oxbEQW.NSRZYqAOq', '검수자(가상)', NULL, 'VIEWER');
INSERT INTO TB_USER_FARM (user_id, farm_id) VALUES (4, 1);
