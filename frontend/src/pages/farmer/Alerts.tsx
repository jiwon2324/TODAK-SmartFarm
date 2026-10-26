import { useCallback, useEffect, useMemo, useState } from 'react';
import { get, patch } from '../../api/client';
import type { Alert } from '../../api/types';
import { ALERT_TYPE_LABEL, fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, Empty, ErrorBox, PageTitle } from '../../components/ui';
import { useFarmStream } from '../../hooks/useApi';
import { useReadOnly } from '../../hooks/auth';

const SEVERITY = [{ k: '', l: '모든 심각도' }, { k: 'CRITICAL', l: '긴급' }, { k: 'WARN', l: '주의' }, { k: 'INFO', l: '안내' }];
const FILTERS = [{ k: '', l: '전체' }, { k: 'OPEN', l: '미확인' }, { k: 'ACK', l: '확인함' }, { k: 'RESOLVED', l: '해결' }];

/** SCR-06 알림 센터 [REQ-F-09, F-06] */
export default function Alerts() {
  const { farmId } = useFarm();
  const [status, setStatus] = useState('');
  const [items, setItems] = useState<Alert[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [severity, setSeverity] = useState('');
  const readOnly = useReadOnly();

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      setItems(await get<Alert[]>(`/api/alerts?farmId=${farmId}${status ? `&status=${status}` : ''}&size=200`));
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId, status]);

  useEffect(() => {
    load();
  }, [load]);
  useFarmStream(farmId, (ev) => {
    if (ev.type === 'alert') load();
  });

  const shown = useMemo(() => items.filter((a) => !severity || a.severity === severity), [items, severity]);

  const set = async (a: Alert, s: 'ACK' | 'RESOLVED') => {
    try {
      await patch(`/api/alerts/${a.alertId}`, { status: s });
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div>
      <PageTitle title="알림 센터" desc="온도·습도 이상, 센서 무응답, 통신 장애, 장치 제어 실패, 벌통 교체 알림. 같은 문제는 해결될 때까지 횟수만 늘어납니다(중복 억제)."
        action={<div className="flex flex-wrap items-center gap-1">
          {FILTERS.map((f) => <Button key={f.k} small variant={status === f.k ? 'primary' : 'secondary'} onClick={() => setStatus(f.k)}>{f.l}</Button>)}
          <select aria-label="심각도" className="ml-1 rounded-lg border border-slate-300 px-2 py-1 text-sm" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITY.map((x) => <option key={x.k} value={x.k}>{x.l}</option>)}
          </select>
        </div>} />
      <ErrorBox msg={err} />
      <Card>
        {shown.length === 0 ? <Empty>알림 없음</Empty> : (
          <ul className="divide-y divide-slate-100">
            {shown.map((a) => (
              <li key={a.alertId} className="flex flex-wrap items-start gap-3 py-3">
                <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:min-w-[220px] sm:flex-col sm:items-start">
                  <Badge tone={a.severity === 'CRITICAL' ? 'red' : a.severity === 'WARN' ? 'amber' : 'blue'}>{ALERT_TYPE_LABEL[a.type] ?? a.type}</Badge>
                  <span className="text-xs text-slate-500">{fmtTime(a.firstAt)}{a.occurCount > 1 && ` · ${a.occurCount}회 (최근 ${fmtTime(a.lastAt)})`}</span>
                </div>
                <div className="min-w-0 flex-1 text-sm text-slate-700">{a.message}</div>
                <div className="flex items-center gap-2">
                  <Badge tone={a.status === 'RESOLVED' ? 'green' : a.status === 'ACK' ? 'gray' : 'red'}>{{ OPEN: '미확인', ACK: '확인함', RESOLVED: '해결' }[a.status]}</Badge>
                  {!readOnly && a.status === 'OPEN' && <Button small variant="secondary" onClick={() => set(a, 'ACK')}>확인</Button>}
                  {!readOnly && a.status !== 'RESOLVED' && <Button small variant="ghost" onClick={() => set(a, 'RESOLVED')}>해결</Button>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
