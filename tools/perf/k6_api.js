// REQ-N-01 성능 측정 (계획서 표 24·KPI): 조회 API p95 ≤ 500ms(7일 데이터), 수동 제어 요청 → ACK p95 ≤ 5초
// 실행: docker run --rm --network todak_default -e PW=... -v "$PWD/tools/perf":/s grafana/k6:0.54.0 run /s/k6_api.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const BASE = __ENV.BASE || 'http://frontend';
const ackTime = new Trend('control_ack_ms', true);

export const options = {
  scenarios: {
    query: { executor: 'constant-vus', vus: 5, duration: '60s', exec: 'query' },
    control: { executor: 'per-vu-iterations', vus: 1, iterations: 20, exec: 'control', startTime: '5s', maxDuration: '5m' },
  },
  thresholds: {
    'http_req_duration{api:series7d}': ['p(95)<500'],
    'http_req_duration{api:dashboard}': ['p(95)<500'],
    control_ack_ms: ['p(95)<5000'],
  },
};

function token(id, pw) {
  const r = http.post(`${BASE}/api/auth/login`, JSON.stringify({ loginId: id, password: pw }), { headers: { 'Content-Type': 'application/json' } });
  return r.json('accessToken');
}

export function setup() {
  return { t: token('farmer01', __ENV.PW) };
}

function iso(d) {
  const p = (n) => String(n).padStart(2, '0');
  const k = new Date(d.getTime() + 9 * 3600 * 1000); // KST
  return `${k.getUTCFullYear()}-${p(k.getUTCMonth() + 1)}-${p(k.getUTCDate())}T${p(k.getUTCHours())}:${p(k.getUTCMinutes())}:00`;
}

export function query(data) {
  const h = { headers: { Authorization: `Bearer ${data.t}` } };
  const to = new Date();
  const from = new Date(to.getTime() - 7 * 86400000);
  const r1 = http.get(`${BASE}/api/sensor-data/series?sensorId=1&from=${iso(from)}&to=${iso(to)}&interval=raw`, Object.assign({ tags: { api: 'series7d' } }, h));
  check(r1, { '7일 원시 조회 200': (r) => r.status === 200 && r.json('points').length > 1000 });
  const r2 = http.get(`${BASE}/api/farms/1/dashboard`, Object.assign({ tags: { api: 'dashboard' } }, h));
  check(r2, { '대시보드 200': (r) => r.status === 200 });
  sleep(0.5);
}

// 보광등 D-LIGHT01을 켜고 끄며 요청 → ACKED까지 걸린 시간 (가상 장치, 시뮬레이터 ACK)
export function control(data) {
  const h = { 'Content-Type': 'application/json', Authorization: `Bearer ${data.t}` };
  const action = __ITER % 2 === 0 ? 'ON' : 'OFF';
  const t0 = Date.now();
  const r = http.post(`${BASE}/api/devices/7/commands`, JSON.stringify({ action, confirm: true, manualMinutes: 10, reason: 'k6 성능 측정' }),
    { headers: Object.assign({ 'Idempotency-Key': `k6-${Date.now()}-${__ITER}` }, h), tags: { api: 'command' } });
  if (!check(r, { '명령 202': (x) => x.status === 202 })) return;
  const id = r.json('commandId');
  for (let i = 0; i < 100; i++) {
    const s = http.get(`${BASE}/api/controls/commands/${id}`, { headers: h, tags: { api: 'commandStatus' } }).json('status');
    if (s === 'ACKED' || s === 'FAILED' || s === 'TIMEOUT') {
      check(s, { ACKED: (x) => x === 'ACKED' });
      ackTime.add(Date.now() - t0);
      break;
    }
    sleep(0.1);
  }
  sleep(1);
}

export function teardown(data) {
  // 측정 후 보광등을 자동 모드로 되돌린다
  http.patch(`${BASE}/api/devices/7/mode`, JSON.stringify({ mode: 'AUTO' }), { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${data.t}` } });
}
