# 시험·실행 증빙

모든 파일은 이 저장소의 스크립트를 실제로 실행해 만든 것이다. 손으로 그린 화면이나 지어낸 수치는 없다. 하우스 센서 값은 가상 센서 시뮬레이터(B안)의 시뮬레이션 데이터이고, 외부 기상 자료(`kma/`)만 기상청 실측이다.

| 파일 | 내용 | 만든 방법 |
|---|---|---|
| [backend_tests.md](backend_tests.md) | 백엔드 JUnit 결과 (클래스·시험별) | `bash tools/run-backend-tests.sh` → `python3 tools/collect_evidence.py` |
| [frontend_tests.txt](frontend_tests.txt) | 프런트 타입 검사 + Vitest | `npx tsc -b && npx vitest run` (node:20 컨테이너) |
| [simulator_tests.txt](simulator_tests.txt) | 시뮬레이터 pytest | `python -m pytest -v tests` |
| [e2e_results.md](e2e_results.md) | Playwright E2E 16단계 (로그인 없이 둘러보기 포함) | `tools/capture_screens.py` |
| [scenario_results.md](scenario_results.md) · [scenario_run_full.log](scenario_run_full.log) · [scenario_run_rerun.log](scenario_run_rerun.log) | 시뮬레이터 시나리오 통합 시험. 전체 실행 중 PC 절전으로 멈춘 고온·저온은 `--only heat,cold`로 다시 실행해 합침 | `tools/scenario_test.py` |
| [performance.md](performance.md) · performance.json · performance_k6.txt | k6 성능 측정 | `tools/perf/k6_api.js` |
| [mysql_queries.md](mysql_queries.md) | 실제 MySQL 조회 결과, 저장 성공률 | `tools/collect_evidence.py` |
| [인수테스트_체크리스트.md](인수테스트_체크리스트.md) | 인수 기준 18항목 검증 방법·결과 | 위 결과 종합 |
| [kma/](kma/) | **기상청 양평(202) 실측 일자료 원본 CSV**와 외부 GDD 손 계산 대조 | data.kma.go.kr에서 내려받아 관리자 화면으로 가져옴 |
| [screenshots/](screenshots/) | 실행 화면 (촬영 시각 `CAPTURED_AT.txt`) | `tools/capture_screens.py` |

결과 구분: 통과 / 실패 / 미실행(이유 적음). 실패나 미실행이 있으면 각 파일에 그대로 남긴다.
