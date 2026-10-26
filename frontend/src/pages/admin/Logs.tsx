import { useEffect, useState } from 'react';
import { get } from '../../api/client';
import type { Command } from '../../api/types';
import { COMMAND_STATUS_LABEL, SOURCE_LABEL, STATE_LABEL, ago, fmtTime } from '../../components/format';
import { Badge, Button, Card, Empty, ErrorBox, PageTitle, Table } from '../../components/ui';

type Tab = 'ingest' | 'commands' | 'deliveries' | 'errors' | 'settings';
const TABS: { k: Tab; l: string }[] = [
  { k: 'ingest', l: '센서 수집 로그' }, { k: 'commands', l: '제어 명령 로그' }, { k: 'deliveries', l: '알림 발송 내역' },
  { k: 'errors', l: '오류·예외 로그' }, { k: 'settings', l: '설정 변경 이력' },
];

/** SCR-A5 시스템·데이터 로그 [REQ-F-09, F-10, F-16] */
export default function Logs() {
  const [tab, setTab] = useState<Tab>('ingest');
  const [data, setData] = useState<unknown>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    const path = { ingest: '/api/admin/logs/ingest', commands: '/api/admin/logs/commands?size=200', deliveries: '/api/admin/logs/deliveries?size=200',
      errors: '/api/admin/logs/errors', settings: '/api/admin/logs/settings?size=200' }[tab];
    get(path).then(setData).catch((e) => setErr(e.message));
  }, [tab]);

  const exportCsv = () => {
    if (!Array.isArray(data) || data.length === 0) return;
    const rows = data as Record<string, unknown>[];
    const keys = Object.keys(rows[0]);
    const csv = '﻿' + [keys.join(','), ...rows.map((r) => keys.map((k) => `"${String(r[k] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `todak_${tab}_log.csv`;
    a.click();
  };

  return (
    <div>
      <PageTitle title="시스템·데이터 로그" action={<div className="flex flex-wrap gap-1">{TABS.map((t) => <Button key={t.k} small variant={tab === t.k ? 'primary' : 'secondary'} onClick={() => setTab(t.k)}>{t.l}</Button>)}</div>} />
      <ErrorBox msg={err} />
      <Card action={Array.isArray(data) && <Button small variant="secondary" onClick={exportCsv}>CSV</Button>}>
        {!data ? <Empty>불러오는 중…</Empty> : tab === 'ingest' ? <Ingest d={data as IngestLog} /> : tab === 'commands' ? <Commands rows={data as Command[]} />
          : tab === 'errors' ? <Errors rows={data as ErrRow[]} /> : <Generic rows={data as Record<string, unknown>[]} />}
      </Card>
    </div>
  );
}

interface IngestLog {
  counters: Record<string, number>;
  sensors: { sensorId: number; farmId: number; sensorCode: string; status: string; installNote: string; lastReceivedAt: string | null; receivedLastHour: number; expectedPerHour: number }[];
}

function Ingest({ d }: { d: IngestLog }) {
  return (
    <>
      <div className="mb-3 flex flex-wrap gap-2 text-sm">
        {Object.entries(d.counters).map(([k, v]) => <Badge key={k}>{{ received: '수신', saved: '저장', duplicates: '중복', rejected: '거부' }[k] ?? k} {v.toLocaleString()}</Badge>)}
        <span className="text-xs text-slate-500">(서버 기동 이후 누계)</span>
      </div>
      <Table head={['농장', '센서', '상태', '최근 1시간', '수신률', '마지막 수신']}>
        {d.sensors.map((s) => {
          const rate = Math.round((s.receivedLastHour / s.expectedPerHour) * 100);
          return (
            <tr key={s.sensorId}>
              <td className="py-1.5 pr-3">{s.farmId}</td>
              <td className="pr-3">{s.sensorCode}</td>
              <td className="pr-3"><Badge tone={s.status === 'ACTIVE' ? 'green' : s.status === 'FAULT' ? 'red' : 'gray'}>{s.status}</Badge></td>
              <td className="pr-3">{s.receivedLastHour}건</td>
              <td className="pr-3">{rate}%</td>
              <td className="pr-3 text-xs">{ago(s.lastReceivedAt)}</td>
            </tr>
          );
        })}
      </Table>
    </>
  );
}

function Commands({ rows }: { rows: Command[] }) {
  if (!rows.length) return <Empty>명령 없음</Empty>;
  return (
    <Table head={['ID', '요청', '장치', '동작', '출처', '상태', '전송', 'ACK', '사유']}>
      {rows.map((c) => (
        <tr key={c.commandId}>
          <td className="py-1.5 pr-3">{c.commandId}</td>
          <td className="whitespace-nowrap pr-3 text-xs">{fmtTime(c.requestedAt)}</td>
          <td className="pr-3">{c.deviceCode}</td>
          <td className="pr-3">{STATE_LABEL[c.action] ?? c.action}</td>
          <td className="pr-3">{SOURCE_LABEL[c.source] ?? c.source}</td>
          <td className="pr-3"><Badge tone={c.status === 'ACKED' ? 'green' : c.status === 'SENT' ? 'amber' : 'red'}>{COMMAND_STATUS_LABEL[c.status] ?? c.status}</Badge></td>
          <td className="whitespace-nowrap pr-3 text-xs">{c.sentAt ? fmtTime(c.sentAt) : '-'}</td>
          <td className="whitespace-nowrap pr-3 text-xs">{c.ackedAt ? fmtTime(c.ackedAt) : '-'}</td>
          <td className="max-w-[280px] truncate pr-3 text-xs text-slate-500" title={c.reason ?? ''}>{c.reason}</td>
        </tr>
      ))}
    </Table>
  );
}

type ErrRow = { at: string; category: string; message: string };
function Errors({ rows }: { rows: ErrRow[] }) {
  if (!rows.length) return <Empty>최근 오류 없음 (메모리 보관 200건, 서버 재시작 시 초기화)</Empty>;
  return (
    <Table head={['시각', '분류', '내용']}>
      {rows.map((r, i) => (
        <tr key={i}><td className="whitespace-nowrap py-1.5 pr-3 text-xs">{fmtTime(r.at)}</td><td className="pr-3"><Badge tone="red">{r.category}</Badge></td><td className="pr-3 text-xs">{r.message}</td></tr>
      ))}
    </Table>
  );
}

function Generic({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <Empty>기록 없음</Empty>;
  const keys = Object.keys(rows[0]);
  return (
    <Table head={keys}>
      {rows.map((r, i) => (
        <tr key={i}>{keys.map((k) => <td key={k} className="whitespace-nowrap py-1.5 pr-3 text-xs">{String(r[k] ?? '')}</td>)}</tr>
      ))}
    </Table>
  );
}
