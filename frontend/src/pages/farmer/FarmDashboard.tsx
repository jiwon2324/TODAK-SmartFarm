import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { get } from '../../api/client';
import type { Alert, Dashboard, Reading, Series } from '../../api/types';
import { ALERT_TYPE_LABEL, METRIC_LABEL, STAGE_LABEL, STATE_LABEL, ago, fmtHm, fmtTime, isActiveState, isoLocal, unit } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Card, ErrorBox, PageTitle, SimNotice } from '../../components/ui';
import { useFarmStream } from '../../hooks/useApi';

const CARD_ORDER = ['S-T01', 'S-T02', 'S-H01', 'S-H02', 'S-CO2-01', 'S-SOL01', 'S-SM01', 'S-SM02', 'S-EC01', 'S-PH01', 'S-TO01'];

/** SCR-02 농가 메인 대시보드: 최신 측정값(카드)과 과거 그래프를 나눠 표시, SSE로 실시간 갱신 [REQ-F-01, F-18] */
export default function FarmDashboard() {
  const { farmId } = useFarm();
  const [d, setD] = useState<Dashboard | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [chart, setChart] = useState<Record<string, number | string>[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const dash = await get<Dashboard>(`/api/farms/${farmId}/dashboard`);
      setD(dash);
      setAlerts(await get<Alert[]>(`/api/alerts?farmId=${farmId}&status=OPEN&size=5`));
      const to = new Date();
      const from = new Date(to.getTime() - 24 * 3600 * 1000);
      const temps = dash.readings.filter((r) => r.metric === 'TEMP' || r.metric === 'HUMI');
      const series = await Promise.all(temps.map((r) =>
        get<Series>(`/api/sensor-data/series?sensorId=${r.sensorId}&from=${isoLocal(from)}&to=${isoLocal(to)}&interval=raw`)));
      const byT = new Map<string, Record<string, number | string>>();
      for (const s of series) {
        for (const p of s.points) {
          const k = p.t;
          const row = byT.get(k) ?? { t: k };
          row[s.sensorCode] = p.value as number;
          byT.set(k, row);
        }
      }
      setChart([...byT.values()].sort((a, b) => String(a.t).localeCompare(String(b.t))));
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);

  useEffect(() => {
    load();
  }, [load]);

  const live = useFarmStream(farmId, (ev) => {
    if (ev.type === 'reading') {
      const r = ev.data as unknown as Reading & { measuredAt: string };
      setD((prev) => prev && {
        ...prev,
        readings: prev.readings.map((x) => (x.sensorId === r.sensorId ? { ...x, value: r.value, measuredAt: r.measuredAt, quality: r.quality, lastReceivedAt: new Date().toISOString(), status: 'ACTIVE' } : x)),
      });
      if (r.metric === 'TEMP' || r.metric === 'HUMI') {
        setChart((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.t === r.measuredAt) return [...prev.slice(0, -1), { ...last, [r.sensorCode]: r.value as number }];
          return [...prev.slice(-1500), { t: r.measuredAt, [r.sensorCode]: r.value as number }];
        });
      }
    } else if (ev.type === 'device') {
      const x = ev.data as { deviceId: number; state: string; mode: string; at: string };
      setD((prev) => prev && { ...prev, devices: prev.devices.map((dv) => (dv.deviceId === x.deviceId ? { ...dv, state: x.state, stateChangedAt: x.at } : dv)) });
    } else if (ev.type === 'alert') {
      get<Alert[]>(`/api/alerts?farmId=${farmId}&status=OPEN&size=5`).then(setAlerts);
    }
  });

  if (!d) return <><ErrorBox msg={err} /><div className="text-slate-500">불러오는 중…</div></>;
  const readings = [...d.readings].sort((a, b) => CARD_ORDER.indexOf(a.sensorCode) - CARD_ORDER.indexOf(b.sensorCode));
  const zoneName = (z: number | null) => d.zones.find((x) => x.zoneId === z)?.zoneCode ?? '공용';
  const gw = d.gateways[0];

  return (
    <div>
      <PageTitle title={`${d.farm.farmName} 대시보드`}
        desc={<>{d.farm.region} · {d.farm.facilityType} {d.farm.areaM2}㎡ · 작기: {d.cropCycle ? `${STAGE_LABEL[d.cropCycle.currentStage]} (정식 ${d.cropCycle.transplantDate})` : '-'}</>}
        action={<div className="flex items-center gap-2 text-sm">
          <Badge tone={gw?.status === 'ONLINE' ? 'green' : 'red'}>게이트웨이 {gw?.gatewayCode} {gw?.status === 'ONLINE' ? '연결' : '단절'}</Badge>
          <Badge tone={live ? 'blue' : 'gray'}>{live ? '실시간 연결' : '실시간 대기'}</Badge>
        </div>} />
      {readings.some((r) => r.simulated) && <SimNotice />}
      <ErrorBox msg={err} />

      <h2 className="mb-2 text-sm font-semibold text-slate-500">현재 측정값 (최신)</h2>
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        {readings.map((r) => {
          const bad = r.status === 'FAULT' || (r.quality && r.quality !== 'OK');
          return (
            <div key={r.sensorId} className={`rounded-xl border bg-white p-3 shadow-sm ${bad ? 'border-red-300' : 'border-slate-200'}`}>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{METRIC_LABEL[r.metric]} · {zoneName(r.zoneId)}</span>
                {bad && <Badge tone="red">{r.status === 'FAULT' ? '무응답' : r.quality}</Badge>}
              </div>
              <div className="mt-1 text-2xl font-bold">{r.value ?? '-'}<span className="ml-1 text-sm font-normal text-slate-500">{unit(r.unit)}</span></div>
              <div className="mt-1 text-[11px] text-slate-400">{r.sensorCode} · {ago(r.measuredAt)}</div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="최근 24시간 온도·습도 (과거 기록)" className="lg:col-span-2">
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart data={chart} margin={{ left: -10, right: 8 }}>
                <CartesianGrid stroke="#eef2f7" />
                <XAxis dataKey="t" tickFormatter={fmtHm} minTickGap={40} fontSize={12} />
                <YAxis yAxisId="t" fontSize={12} domain={['auto', 'auto']} unit="℃" />
                <YAxis yAxisId="h" orientation="right" fontSize={12} domain={[30, 100]} unit="%" />
                <Tooltip labelFormatter={(l) => fmtTime(String(l))} />
                <Legend />
                <Line yAxisId="t" dataKey="S-T01" name="온도 Z1" stroke="#2e7d32" dot={false} strokeWidth={2} isAnimationActive={false} />
                <Line yAxisId="t" dataKey="S-T02" name="온도 Z2" stroke="#e65100" dot={false} strokeWidth={2} isAnimationActive={false} />
                <Line yAxisId="h" dataKey="S-H01" name="습도 Z1" stroke="#1565c0" dot={false} strokeDasharray="4 3" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title={`미해결 알림 ${d.openAlerts}건`} action={<Link className="text-sm text-leaf-700" to="/farm/alerts">전체</Link>}>
          {alerts.length === 0 ? <div className="text-sm text-slate-400">미해결 알림 없음</div> : (
            <ul className="space-y-2">
              {alerts.map((a) => (
                <li key={a.alertId} className="rounded-lg bg-slate-50 p-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge tone={a.severity === 'CRITICAL' ? 'red' : a.severity === 'WARN' ? 'amber' : 'blue'}>{ALERT_TYPE_LABEL[a.type] ?? a.type}</Badge>
                    <span className="text-xs text-slate-400">{fmtTime(a.lastAt)}</span>
                  </div>
                  <div className="mt-1 text-slate-700">{a.message}</div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="장치 작동 상태" className="mt-4" action={<Link className="text-sm text-leaf-700" to="/farm/control">제어하기</Link>}>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {d.devices.map((dv) => (
            <div key={dv.deviceId} className="rounded-lg border border-slate-200 p-2">
              <div className="text-xs text-slate-500">{dv.deviceCode}</div>
              <div className="text-sm font-medium">{dv.deviceName}</div>
              <div className="mt-1 flex items-center gap-1">
                <Badge tone={isActiveState(dv.deviceType, dv.state) ? 'green' : 'gray'}>{STATE_LABEL[dv.state] ?? dv.state}</Badge>
                {dv.mode === 'MANUAL' && <Badge tone="violet">수동</Badge>}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
