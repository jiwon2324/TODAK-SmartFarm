import { useCallback, useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { get, post } from '../../api/client';
import type { Gateway, Series } from '../../api/types';
import { ago, fmtMd, fmtTime, isoLocal } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Card, ConfirmDialog, ErrorBox, PageTitle, Stat } from '../../components/ui';

interface Summary {
  farms: number;
  users: number;
  sensors: { total: number; active: number; fault: number };
  devices: { total: number; byState: Record<string, number>; manual: number };
  gateways: Gateway[];
  lastReceivedAt: string | null;
  receivedLastHour: number;
  ingestCounters: Record<string, number>;
  openAlerts: number;
  commands24h: Record<string, number>;
  mqttConnected: boolean;
  sseSubscribers: number;
}

const SCENARIOS = [
  { k: 'heat', l: '갑작스러운 고온', d: '하우스 내부 온도를 끌어올림 → 환기·안전 한계' },
  { k: 'cold', l: '저온', d: '외부 기온 급강하 → 난방·저온 안전' },
  { k: 'humid', l: '습도 이상', d: '상대습도 +25% → 습도 경보' },
  { k: 'dry', l: '관수 부족', d: '배지 수분 급감 → 자동 관수' },
  { k: 'sensor_silent', l: '센서 무응답', d: 'S-T02 5분 송신 중지 → 무응답 경보' },
  { k: 'disconnect', l: '통신 단절', d: '3분 단절 → 오프라인 경보, 현장 안전 운전, 복구 후 재전송' },
  { k: 'device_fail', l: '장치 오류', d: 'D-FAN01 명령 무시 → 응답 없음(TIMEOUT)' },
  { k: 'recover', l: '정상 복구', d: '모든 시나리오 해제' },
];

/** SCR-A1 관리자 메인 대시보드 + 시뮬레이터 시나리오 [REQ-F-17] */
export default function AdminDashboard() {
  const { farmId, farms } = useFarm();
  const [s, setS] = useState<Summary | null>(null);
  const [chart, setChart] = useState<Record<string, number | string>[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [ask, setAsk] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setS(await get<Summary>('/api/admin/summary'));
      if (farmId) {
        const to = new Date();
        const from = new Date(to.getTime() - 3 * 86400000);
        const ids = [1, 3, 2];
        const series = await Promise.all(ids.map((id) => get<Series>(`/api/sensor-data/series?sensorId=${id}&from=${isoLocal(from)}&to=${isoLocal(to)}&interval=hour`).catch(() => null)));
        const m = new Map<string, Record<string, number | string>>();
        series.forEach((x) => x?.points.forEach((p) => {
          const r = m.get(p.t) ?? { t: p.t };
          r[x.sensorCode] = Math.round((p.avg ?? 0) * 10) / 10;
          m.set(p.t, r);
        }));
        setChart([...m.values()].sort((a, b) => String(a.t).localeCompare(String(b.t))));
      }
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const run = async () => {
    const sc = ask;
    setAsk(null);
    try {
      await post('/api/admin/simulator/scenario', { farmId: 1, scenario: sc });
      setMsg(`시나리오 '${SCENARIOS.find((x) => x.k === sc)?.l}' 를 시뮬레이터에 보냈습니다. 1~3분 안에 대시보드·알림·제어 이력에 반영됩니다.`);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (!s) return <><ErrorBox msg={err} /><div className="text-slate-500">불러오는 중…</div></>;
  const failed = (s.commands24h.FAILED ?? 0) + (s.commands24h.TIMEOUT ?? 0);
  return (
    <div>
      <PageTitle title="관리자 대시보드" desc={`전체 ${s.farms}개 농장 · 사용자 ${s.users}명 · 30초마다 갱신`}
        action={<div className="flex gap-2"><Badge tone={s.mqttConnected ? 'green' : 'red'}>MQTT {s.mqttConnected ? '연결' : '끊김'}</Badge><Badge tone="blue">SSE 구독 {s.sseSubscribers}</Badge></div>} />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="센서 정상 / 전체" value={`${s.sensors.active} / ${s.sensors.total}`} sub={`오류 ${s.sensors.fault}`} tone={s.sensors.fault ? 'red' : undefined} />
        <Stat label="제어 장치" value={s.devices.total} sub={Object.entries(s.devices.byState).map(([k, v]) => `${k} ${v}`).join(' · ') + ` · 수동 ${s.devices.manual}`} />
        <Stat label="최근 데이터 수집" value={ago(s.lastReceivedAt)} sub={`최근 1시간 ${s.receivedLastHour.toLocaleString()}건`} tone={!s.lastReceivedAt || Date.now() - new Date(s.lastReceivedAt).getTime() > 180000 ? 'amber' : undefined} />
        <Stat label="미해결 경보" value={s.openAlerts} tone={s.openAlerts ? 'amber' : undefined} />
        <Stat label="24시간 명령 성공" value={s.commands24h.ACKED ?? 0} sub={`실패·응답없음 ${failed}`} tone={failed ? 'red' : undefined} />
        <Stat label="수신 처리 (기동 후)" value={(s.ingestCounters.saved ?? 0).toLocaleString()} sub={`중복 ${s.ingestCounters.duplicates ?? 0} · 거부 ${s.ingestCounters.rejected ?? 0}`} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title={`${farms.find((f) => f.farmId === farmId)?.farmName ?? ''} 최근 3일 온도 (시간 평균)`} className="lg:col-span-2">
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={chart} margin={{ left: -10, right: 8 }}>
                <CartesianGrid stroke="#eef2f7" />
                <XAxis dataKey="t" tickFormatter={(t) => fmtMd(String(t))} minTickGap={30} fontSize={12} />
                <YAxis yAxisId="t" unit="℃" fontSize={12} />
                <YAxis yAxisId="h" orientation="right" unit="%" fontSize={12} domain={[30, 100]} />
                <Tooltip labelFormatter={(l) => fmtTime(String(l))} />
                <Legend />
                <Line yAxisId="t" dataKey="S-T01" name="온도 Z1" stroke="#2e7d32" dot={false} isAnimationActive={false} />
                <Line yAxisId="t" dataKey="S-T02" name="온도 Z2" stroke="#e65100" dot={false} isAnimationActive={false} />
                <Line yAxisId="h" dataKey="S-H01" name="습도 Z1" stroke="#1565c0" dot={false} strokeDasharray="4 3" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="게이트웨이 상태">
          <ul className="space-y-2 text-sm">
            {s.gateways.map((g) => (
              <li key={g.gatewayId} className="flex items-center justify-between rounded-lg bg-slate-50 p-2">
                <div>
                  <div className="font-medium">{g.gatewayCode} {g.isSimulated && <span className="text-xs text-slate-500">(시뮬레이터)</span>}</div>
                  <div className="text-xs text-slate-500">하트비트 {ago(g.lastHeartbeatAt)} · 기준값 v{g.syncedStdVersion ?? '-'}</div>
                </div>
                <Badge tone={g.status === 'ONLINE' ? 'green' : 'red'}>{g.status}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="시뮬레이터 시나리오 (B안 · 가상 장치에만 적용)" className="mt-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {SCENARIOS.map((x) => (
            <button key={x.k} onClick={() => setAsk(x.k)} className="rounded-lg border border-slate-200 p-3 text-left hover:border-leaf-500 hover:bg-leaf-50">
              <div className="font-medium">{x.l}</div>
              <div className="mt-1 text-xs text-slate-500">{x.d}</div>
            </button>
          ))}
        </div>
      </Card>
      <ConfirmDialog open={!!ask} title="시나리오 실행" body={<>'{SCENARIOS.find((x) => x.k === ask)?.l}' 시나리오를 농장 1의 가상 게이트웨이에 보냅니다. 실제 장비에는 영향이 없습니다.</>}
        onConfirm={run} onCancel={() => setAsk(null)} />
    </div>
  );
}

