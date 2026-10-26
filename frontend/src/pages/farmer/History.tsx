import { useCallback, useEffect, useMemo, useState } from 'react';
import { get } from '../../api/client';
import type { Command, DeviceView, StateLog } from '../../api/types';
import { COMMAND_STATUS_LABEL, SOURCE_LABEL, STATE_LABEL, fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, ErrorBox, PageTitle, Table } from '../../components/ui';
import { useFarmStream } from '../../hooks/useApi';

const statusTone = (s: string) => (s === 'ACKED' ? 'green' : s === 'FAILED' || s === 'TIMEOUT' ? 'red' : 'amber');

/** SCR-05 제어 이력: 장치·출처(자동/수동/안전 한계/현장 안전 운전)·기간 필터, 명령(전송·실행 확인)과 실제 상태 변경을 구분 [REQ-F-10, F-16] */
export default function History() {
  const { farmId } = useFarm();
  const [devices, setDevices] = useState<DeviceView[]>([]);
  const [cmds, setCmds] = useState<Command[]>([]);
  const [logs, setLogs] = useState<StateLog[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [flt, setFlt] = useState({ device: '', source: '', days: 1 });

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const [d, c, l] = await Promise.all([
        get<DeviceView[]>(`/api/devices?farmId=${farmId}`),
        get<Command[]>(`/api/controls/commands?farmId=${farmId}&size=300`),
        get<StateLog[]>(`/api/controls/logs?farmId=${farmId}&size=300`),
      ]);
      setDevices(d);
      setCmds(c);
      setLogs(l);
      setErr(null);
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

  const since = Date.now() - flt.days * 86400000;
  const fCmds = useMemo(() => cmds.filter((c) => (!flt.device || c.deviceCode === flt.device) && (!flt.source || c.source === flt.source)
    && new Date(c.requestedAt).getTime() >= since), [cmds, flt, since]);
  const fLogs = useMemo(() => logs.filter((l) => (!flt.device || l.deviceCode === flt.device) && (!flt.source || l.changedBy === flt.source)
    && new Date(l.changedAt).getTime() >= since), [logs, flt, since]);

  return (
    <div>
      <PageTitle title="제어 이력" desc="명령을 보낸 기록과 장치가 실제로 바뀐 기록을 나눠 보여 줍니다" />
      <ErrorBox msg={err} />
      <Card title="필터">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <select aria-label="장치" className="rounded-lg border border-slate-300 px-2 py-1" value={flt.device} onChange={(e) => setFlt({ ...flt, device: e.target.value })}>
            <option value="">모든 장치</option>
            {devices.map((d) => <option key={d.deviceId} value={d.deviceCode}>{d.deviceName}</option>)}
          </select>
          <select aria-label="출처" className="rounded-lg border border-slate-300 px-2 py-1" value={flt.source} onChange={(e) => setFlt({ ...flt, source: e.target.value })}>
            <option value="">모든 출처</option>
            {Object.entries(SOURCE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {[1, 7, 30].map((n) => (
            <Button key={n} small variant={flt.days === n ? 'primary' : 'secondary'} onClick={() => setFlt({ ...flt, days: n })}>{n === 1 ? '오늘·24시간' : `${n}일`}</Button>
          ))}
          <span className="text-xs text-slate-500">최근 300건 안에서 거릅니다</span>
        </div>
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Card title={`제어 명령 ${fCmds.length}건 (전송·실행 확인 구분)`}>
          <Table head={['시각', '장치', '동작', '출처', '상태', '사유']}>
            {fCmds.map((c) => (
              <tr key={c.commandId}>
                <td className="whitespace-nowrap py-1.5 pr-3">{fmtTime(c.requestedAt)}</td>
                <td className="pr-3">{c.deviceName}</td>
                <td className="pr-3">{STATE_LABEL[c.action] ?? c.action}</td>
                <td className="pr-3">{SOURCE_LABEL[c.source] ?? c.source}</td>
                <td className="pr-3"><Badge tone={statusTone(c.status)}>{COMMAND_STATUS_LABEL[c.status] ?? c.status}{c.retryCount ? ' (재전송)' : ''}</Badge></td>
                <td className="max-w-[260px] truncate pr-3 text-xs text-slate-500" title={c.reason ?? ''}>{c.reason}</td>
              </tr>
            ))}
          </Table>
        </Card>
        <Card title={`장치 상태 변경 이력 ${fLogs.length}건 (실제 동작)`}>
          <Table head={['시각', '장치', '변경', '원인']}>
            {fLogs.map((l) => (
              <tr key={l.logId}>
                <td className="whitespace-nowrap py-1.5 pr-3">{fmtTime(l.changedAt)}</td>
                <td className="pr-3">{l.deviceName}</td>
                <td className="pr-3">{STATE_LABEL[l.prevState ?? ''] ?? l.prevState} → {STATE_LABEL[l.newState] ?? l.newState}</td>
                <td className="pr-3">{SOURCE_LABEL[l.changedBy] ?? l.changedBy}{l.commandId ? ` #${l.commandId}` : ''}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>

    </div>
  );
}
