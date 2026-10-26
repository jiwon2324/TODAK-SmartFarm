import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { get, newIdempotencyKey, patch, post } from '../../api/client';
import type { Command, DeviceView } from '../../api/types';
import { COMMAND_STATUS_LABEL, SOURCE_LABEL, STATE_LABEL, fmtTime, isActiveState } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, ConfirmDialog, ErrorBox, PageTitle, Table } from '../../components/ui';
import { useFarmStream } from '../../hooks/useApi';
import { useReadOnly } from '../../hooks/auth';

const GROUPS: { title: string; types: string[] }[] = [
  { title: '환기 (측창·환풍기)', types: ['VENT', 'FAN'] },
  { title: '난방', types: ['HEATER'] },
  { title: '광 (보광등·차광막)', types: ['LIGHT', 'SHADE'] },
  { title: '관수·양액', types: ['VALVE', 'NUTRIENT'] },
];

const statusTone = (s: string) => (s === 'ACKED' ? 'green' : s === 'FAILED' || s === 'TIMEOUT' ? 'red' : 'amber');

/** SCR-04 장치 제어: 수동 제어(확인 절차), 자동/수동 전환, 명령 상태(전송≠실행), 제어 이력 [REQ-F-08, F-16] */
export default function Control() {
  const { farmId } = useFarm();
  const [devices, setDevices] = useState<DeviceView[]>([]);
  const [cmds, setCmds] = useState<Command[]>([]);

  const [err, setErr] = useState<string | null>(null);
  const [ask, setAsk] = useState<{ d: DeviceView; action: 'ON' | 'OFF' } | null>(null);
  const [minutes, setMinutes] = useState(60);
  const readOnly = useReadOnly();

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      setDevices(await get<DeviceView[]>(`/api/devices?farmId=${farmId}`));
      setCmds(await get<Command[]>(`/api/controls/commands?farmId=${farmId}&size=10`));
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);

  useEffect(() => {
    load();
  }, [load]);

  useFarmStream(farmId, (ev) => {
    if (ev.type === 'device' || ev.type === 'command') load();
  });

  const send = async () => {
    if (!ask) return;
    const { d, action } = ask;
    setAsk(null);
    try {
      await post(`/api/devices/${d.deviceId}/commands`, { action, confirm: true, manualMinutes: minutes, reason: '웹 수동 제어' },
        { 'Idempotency-Key': newIdempotencyKey() });
      setErr(null);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const toggleMode = async (d: DeviceView) => {
    try {
      await patch(`/api/devices/${d.deviceId}/mode`, d.mode === 'AUTO' ? { mode: 'MANUAL', manualMinutes: minutes } : { mode: 'AUTO' });
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const label = (d: DeviceView, on: boolean) => (d.deviceType === 'VENT' ? (on ? '열기' : '닫기') : d.deviceType === 'SHADE' ? (on ? '차광' : '걷기') : on ? '켜기' : '끄기');

  return (
    <div>
      <PageTitle title="장치 제어" desc="버튼을 누르면 명령이 전송되고, 장치가 실행을 확인(ACK)해야 상태가 바뀝니다. 수동 조작한 장치는 정한 시간 동안 자동 제어가 멈춥니다(안전 한계 제외)."
        action={<label className="flex items-center gap-2 text-sm">수동 유지
          <select className="rounded border border-slate-300 px-2 py-1" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
            {[10, 30, 60, 120].map((m) => <option key={m} value={m}>{m}분</option>)}
          </select></label>} />
      <ErrorBox msg={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        {GROUPS.map((g) => (
          <Card key={g.title} title={g.title}>
            <div className="space-y-2">
              {devices.filter((d) => g.types.includes(d.deviceType)).map((d) => {
                const on = isActiveState(d.deviceType, d.state);
                return (
                  <div key={d.deviceId} className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 p-2.5">
                    <div className="min-w-[140px] flex-1">
                      <div className="font-medium">{d.deviceName}</div>
                      <div className="text-xs text-slate-500">{d.deviceCode} · 변경 {fmtTime(d.stateChangedAt)}</div>
                    </div>
                    <Badge tone={on ? 'green' : 'gray'}>{STATE_LABEL[d.state] ?? d.state}</Badge>
                    <button onClick={() => toggleMode(d)} disabled={readOnly} className={`rounded-full px-2 py-0.5 text-xs ring-1 ${d.mode === 'AUTO' ? 'bg-sky-50 text-sky-800 ring-sky-100' : 'bg-violet-50 text-violet-700 ring-violet-100'}`}
                      title="자동/수동 전환">{d.mode === 'AUTO' ? '자동' : `수동 ~${fmtTime(d.manualUntil).slice(-5)}`}</button>
                    <Button small onClick={() => setAsk({ d, action: 'ON' })} disabled={on || readOnly} title={readOnly ? '조회 전용 계정' : undefined}>{label(d, true)}</Button>
                    <Button small variant="secondary" onClick={() => setAsk({ d, action: 'OFF' })} disabled={!on || readOnly} title={readOnly ? '조회 전용 계정' : undefined}>{label(d, false)}</Button>
                  </div>
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      <Card className="mt-4" title="방금 보낸 명령 (최근 10건)" action={<Link to="/farm/history" className="text-sm text-leaf-700 underline">제어 이력 전체</Link>}>
        <Table head={['시각', '장치', '동작', '출처', '상태']}>
          {cmds.slice(0, 10).map((x) => (
            <tr key={x.commandId}>
              <td className="whitespace-nowrap py-1.5 pr-3">{fmtTime(x.requestedAt)}</td>
              <td className="pr-3">{x.deviceName}</td>
              <td className="pr-3">{STATE_LABEL[x.action] ?? x.action}</td>
              <td className="pr-3">{SOURCE_LABEL[x.source] ?? x.source}</td>
              <td className="pr-3"><Badge tone={statusTone(x.status)}>{COMMAND_STATUS_LABEL[x.status] ?? x.status}{x.retryCount ? ' (재전송)' : ''}</Badge></td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-xs text-slate-500">'전송됨'은 명령을 보냈다는 뜻이고, 장치가 실행을 확인해야 '실행 확인'이 됩니다.</p>
      </Card>

      <ConfirmDialog open={!!ask} title="장치 제어 확인"
        body={ask && <>
          <b>{ask.d.deviceName}</b>을(를) <b>{label(ask.d, ask.action === 'ON')}</b> 하시겠습니까?<br />
          {minutes}분 동안 이 장치의 자동 제어가 멈춥니다. 현재 연결은 <b>가상 장치(시뮬레이터)</b>입니다.
        </>}
        danger={ask?.d.deviceType === 'HEATER' || ask?.d.deviceType === 'VALVE' || ask?.d.deviceType === 'NUTRIENT'}
        confirmLabel="전송" onConfirm={send} onCancel={() => setAsk(null)} />
    </div>
  );
}
