-- 통합 테스트 전용 DB(todak_test). 운영 DB(todak)와 분리해 테스트가 실제 데이터를 지우지 않게 한다.
-- DB 사용자 이름을 .env의 DB_USER에서 바꿨다면 아래 'todak'도 같이 바꾼다.
CREATE DATABASE IF NOT EXISTS todak_test DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON todak_test.* TO 'todak'@'%';
FLUSH PRIVILEGES;
