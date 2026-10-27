# 성능 측정 결과 (REQ-N-01)

- 측정: 2026-10-27 07:56 KST · k6 0.54.0 (`tools/perf/k6_api.js`) · 대상 http://frontend (nginx → Spring Boot → MySQL)
- 환경: 개발 PC 1대의 Docker Compose (운영 서버 값 아님). 센서 데이터는 시뮬레이터가 만든 약 2.2만 건 이상
- 부하: 조회 가상 사용자 5명 60초 동시 + 제어 1명 20회(보광등 D-LIGHT01 ON/OFF, 가상 장치 ACK)

| 항목 | 목표 | p95 | 평균 | 판정 |
|---|---|---|---|---|
| 7일 원시 데이터 조회 (센서 1개, 1분 실시간 + 10분 백필 구간 혼재) | ≤ 500 ms | 29.1 ms | 22.3 ms | 통과 |
| 대시보드 조회 | ≤ 500 ms | 39.9 ms | - | 통과 |
| 수동 제어 요청 → 실행 확인(ACK) | ≤ 5,000 ms | 485 ms | 464 ms (최대 486) | 통과 |
| HTTP 실패율 | 0 % | 0.00 % (요청 1212건) | - | 통과 |
| 검사(check) 통과율 | 100 % | 100.00 % | - | 통과 |

k6 원본 출력: [performance_k6.txt](performance_k6.txt), 요약 JSON: performance.json
