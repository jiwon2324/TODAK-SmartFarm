import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Maximize2, Minimize2 } from 'lucide-react';
import { get } from '../../api/client';
import type { Alert, Command, Dashboard, DeviceView } from '../../api/types';
import { COMMAND_STATUS_LABEL, METRIC_LABEL, SOURCE_LABEL, STAGE_LABEL, STATE_LABEL, ago, fmtTime, isActiveState, unit } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Card, ErrorBox, SimNotice } from '../../components/ui';
import { useFarmStream } from '../../hooks/useApi';
import { BED_ROWS, BED_X, DEVICE_SPOTS, HOUSE, PANEL_SPOT, SENSOR_SPOTS, ZONE_SPLIT, toSvg } from './layout';

export type Level = 'OK' | 'WARN' | 'ALARM' | 'STALE' | 'NODATA';
export interface SensorJudge {
  sensorId: number; sensorCode: string; metric: string; unit: string; zoneId: number | null;
  value: number | null; measuredAt: string | null; quality: string | null; level: Level; note: string; lo: number | null; hi: number | null;
}
export interface MonitorEvent { at: string; kind: 'ALERT' | 'COMMAND' | 'STATE'; severity: string; text: string; status: string; ref: string; live?: boolean }
export interface MonitorSnapshot {
  serverTime: string; day: boolean; stage: string | null; stdVersion: number | null; overall: 'OK' | 'WARN' | 'ALARM';
  summary: Record<Level, number>; sensors: SensorJudge[]; events: MonitorEvent[];
}

// 판정 색: 색만으로 구분하지 않도록 글자(정상·주의·경보·끊김)를 항상 함께 쓴다
export const LEVEL: Record<Level, { label: string; fill: string; stroke: string; tone: 'green' | 'amber' | 'red' | 'gray' }> = {
  OK: { label: '정상', fill: '#2e7d32', stroke: '#1b5e20', tone: 'green' },
  WARN: { label: '주의', fill: '#f59e0b', stroke: '#b45309', tone: 'amber' },
  ALARM: { label: '경보', fill: '#dc2626', stroke: '#991b1b', tone: 'red' },
  STALE: { label: '끊김', fill: '#94a3b8', stroke: '#475569', tone: 'gray' },
  NODATA: { label: '값 없음', fill: '#e2e8f0', stroke: '#94a3b8', tone: 'gray' },
};
const KIND_LABEL = { ALERT: '경보', COMMAND: '명령', STATE: '상태' } as const;

export function fmtValue(v: number | null | undefined, metric: string) {
  if (v === null || v === undefined) return '-';
  return metric === 'CO2' || metric === 'SOLAR' ? String(Math.round(v)) : (Math.round(v * 10) / 10).toFixed(1);
}

/** SCR-M1 통합 관제: 하우스 평면(PPT 배치도) 위에 센서 판정·장치 상태를 실시간으로 겹쳐 보여 주는 상황판 [REQ-F-01, F-06, F-08, F-09, F-18] */
export default function Monitor() {
  const { farmId } = useFarm();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [mon, setMon] = useState<MonitorSnapshot | null>(null);
  const [live, setLive] = useState<MonitorEvent[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [now, setNow] = useState(new Date());
  const [full, setFull] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const refetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const [d, m] = await Promise.all([get<Dashboard>(`/api/farms/${farmId}/dashboard`), get<MonitorSnapshot>(`/api/farms/${farmId}/monitor`)]);
      setDash(d);
      setMon(m);
      setLive([]); // 서버 타임라인에 이미 들어간 실시간 이벤트는 버린다
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);

  // 판정은 서버가 한다: 새 값이 오면 3초 모아서 다시 받는다
  const soon = useCallback(() => {
    if (refetchTimer.current) return;
    refetchTimer.current = setTimeout(() => {
      refetchTimer.current = null;
      load();
    }, 3000);
  }, [load]);

  useEffect(() => {
    document.title = '통합 관제 · TODAK';
    load();
    const t = setInterval(load, 30000);
    const c = setInterval(() => setNow(new Date()), 1000);
    return () => {
      clearInterval(t);
      clearInterval(c);
      if (refetchTimer.current) clearTimeout(refetchTimer.current);
      refetchTimer.current = null;
    };
  }, [load]);

  useEffect(() => {
    const on = () => setFull(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', on);
    return () => document.removeEventListener('fullscreenchange', on);
  }, []);

  const connected = useFarmStream(farmId, (ev) => {
    if (ev.type === 'reading') {
      const r = ev.data as { sensorId: number; value: number; measuredAt: string; quality: string };
      // 값은 바로 바꾸고(판정은 그대로), 판정은 곧 서버에서 다시 받는다
      setMon((p) => p && { ...p, sensors: p.sensors.map((s) => (s.sensorId === r.sensorId ? { ...s, value: r.value, measuredAt: r.measuredAt, quality: r.quality } : s)) });
      soon();
    } else if (ev.type === 'device') {
      const x = ev.data as { deviceId: number; state: string; mode: string; at: string };
      setDash((p) => p && { ...p, devices: p.devices.map((d) => (d.deviceId === x.deviceId ? { ...d, state: x.state, mode: x.mode as DeviceView['mode'], stateChangedAt: x.at } : d)) });
      const d = dash?.devices.find((v) => v.deviceId === x.deviceId);
      push({ at: x.at, kind: 'STATE', severity: 'INFO', text: `${d?.deviceName ?? x.deviceId} → ${STATE_LABEL[x.state] ?? x.state}`, status: x.mode, ref: d?.deviceCode ?? '', live: true });
    } else if (ev.type === 'command') {
      const c = ev.data as unknown as Command;
      push({ at: c.requestedAt, kind: 'COMMAND', severity: c.status === 'FAILED' || c.status === 'TIMEOUT' ? 'WARN' : 'INFO',
        text: `${c.deviceName} ${STATE_LABEL[c.action] ?? c.action} 명령 (${SOURCE_LABEL[c.source] ?? c.source})`, status: c.status, ref: c.deviceCode, live: true });
    } else if (ev.type === 'alert') {
      const a = ev.data as unknown as Alert;
      push({ at: a.lastAt, kind: 'ALERT', severity: a.severity, text: a.message, status: a.status, ref: a.type, live: true });
      soon();
    }
  });

  const push = (e: MonitorEvent) => setLive((p) => [e, ...p].slice(0, 30));

  const toggleFull = () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else wrap.current?.requestFullscreen?.();
  };

  if (!mon || !dash) return <><ErrorBox msg={err} /><div className="text-slate-500">불러오는 중…</div></>;

  const events = [...live, ...mon.events].slice(0, 30);
  const selected = mon.sensors.find((s) => s.sensorCode === sel);
  const gw = dash.gateways;
  const overallTone = mon.overall === 'ALARM' ? 'red' : mon.overall === 'WARN' ? 'amber' : 'green';
  const overallLabel = mon.overall === 'ALARM' ? '경보' : mon.overall === 'WARN' ? '주의' : '정상';
  const zoneCode = (z: number | null) => dash.zones.find((x) => x.zoneId === z)?.zoneCode ?? '공용';

  return (
    <div ref={wrap} className={full ? 'h-full overflow-auto bg-slate-50 p-4' : ''}>
      {/* 상단 상태줄 */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">통합 관제 <span className="text-base font-medium text-slate-500">{dash.farm.farmName}</span></h1>
          <p className="text-sm text-slate-500">
            <time className="font-mono">{now.toLocaleString('ko-KR', { hour12: false })}</time> · {mon.day ? '주간' : '야간'} 기준 · 생육 단계 {mon.stage ? STAGE_LABEL[mon.stage] ?? mon.stage : '-'} · 기준값 v{mon.stdVersion ?? '-'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className={`rounded-lg px-3 py-1.5 text-base font-bold text-white ${overallTone === 'red' ? 'bg-red-600' : overallTone === 'amber' ? 'bg-amber-500' : 'bg-leaf-600'}`} role="status" aria-live="polite">종합 {overallLabel}</span>
          {gw.map((g) => <Badge key={g.gatewayId} tone={g.status === 'ONLINE' ? 'green' : 'red'}>{g.gatewayCode} {g.status === 'ONLINE' ? '연결' : '단절'}</Badge>)}
          <Badge tone={connected ? 'blue' : 'gray'}>{connected ? '● 실시간' : '○ 재연결 중'}</Badge>
          <button type="button" onClick={toggleFull} className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-sm ring-1 ring-slate-300 hover:bg-white" aria-label={full ? '전체 화면 끝내기' : '전체 화면'}>
            {full ? <Minimize2 size={16} /> : <Maximize2 size={16} />}{full ? '창 모드' : '전체 화면'}
          </button>
        </div>
      </div>
      {dash.readings.some((r) => r.simulated) && <SimNotice />}
      <ErrorBox msg={err} />

      {/* 판정 요약 */}
      <div className="mb-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
        {(['ALARM', 'WARN', 'OK', 'STALE'] as Level[]).map((k) => (
          <div key={k} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <div className="flex items-center gap-1.5 text-xs text-slate-500"><span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: LEVEL[k].fill }} />센서 {LEVEL[k].label}</div>
            <div className="text-2xl font-bold">{mon.summary[k] ?? 0}</div>
          </div>
        ))}
        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="text-xs text-slate-500">미해결 경보</div>
          <div className={`text-2xl font-bold ${dash.openAlerts ? 'text-red-600' : ''}`}>{dash.openAlerts}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="text-xs text-slate-500">마지막 수신</div>
          <div className="text-lg font-bold">{ago(dash.lastReceivedAt)}</div>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_340px]">
        <div className="min-w-0 space-y-3">
          <Card title="하우스 평면 · 실시간" action={<span className="text-xs text-slate-500">센서·장치를 누르면 자세히 보입니다</span>}>
            <div className="overflow-x-auto">
              <HouseMap mon={mon} devices={dash.devices} selected={sel} onSelect={setSel} />
            </div>
            <Legend />
            {selected && (
              <div className="mt-2 rounded-lg bg-slate-50 p-3 text-sm" aria-live="polite">
                <div className="flex flex-wrap items-center gap-2">
                  <b>{selected.sensorCode}</b> {METRIC_LABEL[selected.metric]} · {zoneCode(selected.zoneId)}
                  <Badge tone={LEVEL[selected.level].tone}>{LEVEL[selected.level].label}</Badge>
                </div>
                <div className="mt-1 text-slate-600">
                  현재 <b className="text-slate-900">{fmtValue(selected.value, selected.metric)}{unit(selected.unit)}</b>
                  {(selected.lo !== null || selected.hi !== null) && <> · 기준 {selected.lo ?? '…'} ~ {selected.hi ?? '…'}{unit(selected.unit)}</>}
                  {' · '}{selected.note} · {ago(selected.measuredAt)}
                  {' · '}<Link className="text-leaf-700 underline" to="/farm/graph">그래프</Link>
                </div>
              </div>
            )}
          </Card>

          <Card title="센서 판정">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6">
              {mon.sensors.map((s) => (
                <button key={s.sensorId} type="button" onClick={() => setSel(s.sensorCode)}
                  className={`rounded-lg border-l-4 bg-white p-2.5 text-left ring-1 ring-slate-200 hover:bg-slate-50 ${sel === s.sensorCode ? 'outline outline-2 outline-leaf-500' : ''}`}
                  style={{ borderLeftColor: LEVEL[s.level].fill }}>
                  <div className="flex items-center justify-between text-xs text-slate-500"><span>{METRIC_LABEL[s.metric]} · {zoneCode(s.zoneId)}</span><span>{LEVEL[s.level].label}</span></div>
                  <div className="text-xl font-bold">{fmtValue(s.value, s.metric)}<span className="ml-0.5 text-xs font-normal text-slate-500">{unit(s.unit)}</span></div>
                  <div className="truncate text-xs text-slate-500" title={s.note}>{s.sensorCode} · {s.note}</div>
                </button>
              ))}
            </div>
          </Card>

          <Card title="제어 장치" action={<Link to="/farm/control" className="text-sm text-leaf-700 underline">장치 제어로 이동</Link>}>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6">
              {dash.devices.map((d) => {
                const on = isActiveState(d.deviceType, d.state);
                return (
                  <div key={d.deviceId} className={`rounded-lg p-2.5 ring-1 ${on ? 'bg-leaf-50 ring-leaf-100' : 'bg-white ring-slate-200'}`}>
                    <div className="flex items-center justify-between text-xs text-slate-500"><span>{d.deviceCode}</span>{d.mode === 'MANUAL' && <Badge tone="violet">수동</Badge>}</div>
                    <div className="truncate text-sm font-medium">{d.deviceName}</div>
                    <div className={`text-sm font-bold ${on ? 'text-leaf-700' : 'text-slate-500'}`}>{STATE_LABEL[d.state] ?? d.state}</div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        <Card title="실시간 이벤트" className="xl:max-h-[calc(100vh-180px)] xl:overflow-y-auto" action={<Link to="/farm/alerts" className="text-sm text-leaf-700 underline">알림</Link>}>
          {!events.length ? <p className="text-sm text-slate-500">최근 이벤트 없음</p> : (
            <ol className="space-y-1.5" aria-label="최근 이벤트">
              {events.map((e, i) => (
                <li key={`${e.kind}-${e.at}-${i}`} className={`rounded-lg border-l-4 bg-white p-2 text-sm ring-1 ring-slate-100 ${e.live ? 'animate-[pulse_1.5s_ease-in-out_1]' : ''}`}
                  style={{ borderLeftColor: e.severity === 'CRITICAL' ? '#dc2626' : e.severity === 'WARN' ? '#f59e0b' : '#94a3b8' }}>
                  <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                    <span>{KIND_LABEL[e.kind]} · {e.ref}</span><time>{fmtTime(e.at)}</time>
                  </div>
                  <div className="text-slate-800">{e.text}</div>
                  <div className="text-xs text-slate-500">{e.kind === 'COMMAND' ? COMMAND_STATUS_LABEL[e.status] ?? e.status : e.kind === 'ALERT' ? ({ OPEN: '미해결', ACK: '확인', RESOLVED: '해결' } as Record<string, string>)[e.status] ?? e.status : SOURCE_LABEL[e.status] ?? e.status}</div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
      {(Object.keys(LEVEL) as Level[]).map((k) => (
        <span key={k} className="inline-flex items-center gap-1"><span className="inline-block h-3 w-3 rounded-full ring-1" style={{ background: LEVEL[k].fill, borderColor: LEVEL[k].stroke }} />{LEVEL[k].label}</span>
      ))}
      <span className="inline-flex items-center gap-1"><span className="inline-block h-3 w-3 bg-leaf-600" />장치 작동</span>
      <span className="inline-flex items-center gap-1"><span className="inline-block h-3 w-3 border border-slate-500 bg-white" />장치 정지</span>
      <span className="inline-flex items-center gap-1"><span className="inline-block h-3 w-3 bg-red-700" />제어반 CP-01</span>
    </div>
  );
}

/** PPT 배치도를 그대로 옮긴 하우스 평면 (SVG). 위치가 정해지지 않은 센서·장치는 그리지 않고 아래 목록에만 나온다 */
function HouseMap({ mon, devices, selected, onSelect }: { mon: MonitorSnapshot; devices: DeviceView[]; selected: string | null; onSelect: (c: string) => void }) {
  const H = HOUSE;
  const panel = toSvg(PANEL_SPOT);
  return (
    <svg viewBox="0 0 1000 330" className="min-w-[720px]" role="img" aria-label="하우스 평면도: 센서 판정과 장치 상태">
      <rect x={H.x} y={H.y} width={(H.w * ZONE_SPLIT) / 100} height={H.h} fill="#f1f8f1" />
      <rect x={H.x + (H.w * ZONE_SPLIT) / 100} y={H.y} width={(H.w * (100 - ZONE_SPLIT)) / 100} height={H.h} fill="#eff6fd" />
      <rect x={H.x} y={H.y} width={H.w} height={H.h} fill="none" stroke="#334155" strokeWidth={2} />
      <line x1={H.x + (H.w * ZONE_SPLIT) / 100} x2={H.x + (H.w * ZONE_SPLIT) / 100} y1={H.y} y2={H.y + H.h} stroke="#64748b" strokeDasharray="6 4" />
      <text x={H.x + (H.w * ZONE_SPLIT) / 200} y={20} textAnchor="middle" fontSize={14} fontWeight={700} fill="#2e7d32">Z1 입구측</text>
      <text x={H.x + H.w * 0.75} y={20} textAnchor="middle" fontSize={14} fontWeight={700} fill="#1565c0">Z2 안쪽</text>
      {BED_ROWS.map((y) => (
        <rect key={y} x={H.x + (H.w * BED_X[0]) / 100} y={H.y + (H.h * y) / 100 - 4} width={(H.w * (BED_X[1] - BED_X[0])) / 100} height={8} fill="#c8e6c9" stroke="#81c784" />
      ))}
      <rect x={H.x - 6} y={H.y + H.h / 2 - 20} width={6} height={40} fill="#e65100" />
      <text x={H.x - 10} y={H.y + H.h / 2 + 34} textAnchor="end" fontSize={11} fill="#475569">출입구</text>
      {/* 제어반 → RS-485 간선 */}
      <line x1={panel.x} x2={H.x + H.w - 4} y1={panel.y} y2={panel.y} stroke="#e65100" strokeDasharray="5 4" opacity={0.5} />
      <rect x={panel.x - 7} y={panel.y - 7} width={14} height={14} fill="#b91c1c" />
      <text x={panel.x + 10} y={panel.y - 9} fontSize={10} fill="#7f1d1d">CP-01</text>

      {devices.map((d) => {
        const spot = DEVICE_SPOTS[d.deviceCode];
        if (!spot) return null;
        const p = toSvg(spot);
        const on = isActiveState(d.deviceType, d.state);
        return (
          <g key={d.deviceId}>
            <title>{`${d.deviceName} (${d.deviceCode}) · ${STATE_LABEL[d.state] ?? d.state} · ${d.mode === 'MANUAL' ? '수동' : '자동'}`}</title>
            <rect x={p.x - 9} y={p.y - 9} width={18} height={18} rx={2} fill={on ? '#2e7d32' : '#ffffff'} stroke={on ? '#1b5e20' : '#475569'} strokeWidth={1.5} />
            {d.mode === 'MANUAL' && <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={11} fontWeight={700} fill={on ? '#fff' : '#6d28d9'}>M</text>}
            <text x={p.x} y={p.y + (spot.y > 90 ? -13 : 22)} textAnchor="middle" fontSize={10} fill="#334155">{d.deviceCode.replace('D-', '')}</text>
          </g>
        );
      })}

      {mon.sensors.map((s) => {
        const spot = SENSOR_SPOTS[s.sensorCode];
        if (!spot) return null;
        const p = toSvg(spot);
        const L = LEVEL[s.level];
        const isSel = selected === s.sensorCode;
        return (
          <g key={s.sensorId} role="button" tabIndex={0} aria-label={`${s.sensorCode} ${METRIC_LABEL[s.metric]} ${fmtValue(s.value, s.metric)}${unit(s.unit)} ${L.label}`}
            onClick={() => onSelect(s.sensorCode)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(s.sensorCode)} style={{ cursor: 'pointer' }}>
            <title>{`${s.sensorCode} · ${s.note}`}</title>
            {s.level === 'ALARM' && (
              <circle cx={p.x} cy={p.y} r={13} fill="none" stroke={L.fill} strokeWidth={2}>
                <animate attributeName="r" values="13;24;13" dur="1.6s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="1;0;1" dur="1.6s" repeatCount="indefinite" />
              </circle>
            )}
            <circle cx={p.x} cy={p.y} r={isSel ? 14 : 12} fill={L.fill} stroke={isSel ? '#0f172a' : L.stroke} strokeWidth={isSel ? 3 : 1.5}
              strokeDasharray={s.level === 'STALE' ? '3 2' : undefined} />
            <text x={p.x} y={p.y - 18} textAnchor="middle" fontSize={10} fill="#334155">{s.sensorCode.replace('S-', '')}</text>
            <rect x={p.x - 26} y={p.y + 15} width={52} height={17} rx={4} fill="#ffffff" stroke={L.stroke} opacity={0.95} />
            <text x={p.x} y={p.y + 28} textAnchor="middle" fontSize={11} fontWeight={700} fill="#0f172a">{fmtValue(s.value, s.metric)}{unit(s.unit)}</text>
          </g>
        );
      })}
    </svg>
  );
}
