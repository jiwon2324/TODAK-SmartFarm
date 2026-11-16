import { useCallback, useEffect, useState } from 'react';
import { get } from '../../api/client';
import { gaEnabled, measurementId } from '../../analytics';
import { ago, fmtTime } from '../../components/format';
import { Badge, Button, Card, Empty, ErrorBox, PageTitle, Stat, Table } from '../../components/ui';

type Status = 'OK' | 'WARN' | 'FAIL';
interface Check { key: string; label: string; status: Status; detail: string; action: string }
interface Ops {
  checkedAt: string;
  overall: Status;
  summary: Record<Status, number>;
  checks: Check[];
  server: { version: string; builtAt: string | null; startedAt: string; uptimeSec: number; timeZone: string; java: string;
    memUsedBytes: number; memMaxBytes: number; diskTotalBytes: number; diskFreeBytes: number; diskFreeRatio: number };
  database: { version: string; migration: string; totalBytes: number; sensorDataRows: number; tables: { name: string; approxRows: number; bytes: number }[] };
  backup: { dir: string; dirMounted: boolean; count: number; lastFile: string | null; lastAt: string | null; files: { file: string; bytes: number; at: string }[] };
  retention: { rawDays: number; oldestRaw: string };
  ingestCounters: Record<string, number>;
}

const TONE: Record<Status, 'green' | 'amber' | 'red'> = { OK: 'green', WARN: 'amber', FAIL: 'red' };
const LABEL: Record<Status, string> = { OK: '정상', WARN: '확인 필요', FAIL: '즉시 조치' };

export const mb = (b: number) => (b >= 1024 ** 3 ? `${(b / 1024 ** 3).toFixed(1)} GB` : `${(b / 1024 ** 2).toFixed(1)} MB`);
export function uptime(sec: number) {
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return d ? `${d}일 ${h}시간` : h ? `${h}시간 ${m}분` : `${m}분`;
}

/** SCR-A7 운영 점검 — 운영 매뉴얼 3장 '일일 점검'을 서버가 자동 판정한 결과 [운영 이관] */
export default function OpsPage() {
  const [o, setO] = useState<Ops | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setO(await get<Ops>('/api/admin/ops'));
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, []);

  useEffect(() => {
    document.title = '운영 점검 · TODAK';
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  // 일일 점검 기록용 CSV (운영 매뉴얼 부록 '일일 점검표'에 붙인다)
  const exportCsv = () => {
    if (!o) return;
    const rows = [['점검 시각', '항목', '판정', '내용', '조치 절차'], ...o.checks.map((c) => [fmtTime(o.checkedAt), c.label, LABEL[c.status], c.detail, c.action])];
    const csv = '﻿' + rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `todak_daily_check_${o.checkedAt.slice(0, 10)}.csv`;
    a.click();
  };

  if (!o) return <><ErrorBox msg={err} /><div className="text-slate-500">불러오는 중…</div></>;
  const s = o.server;
  const ga = measurementId();
  return (
    <div>
      <PageTitle title="운영 점검" desc={<>일일 점검 항목 자동 판정 · {fmtTime(o.checkedAt)} 기준 · 1분마다 갱신</>}
        action={<div className="flex flex-wrap gap-2"><Button small variant="secondary" onClick={load}>다시 점검</Button><Button small onClick={exportCsv}>점검표 CSV</Button></div>} />
      <ErrorBox msg={err} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="종합 판정" value={LABEL[o.overall]} tone={o.overall === 'FAIL' ? 'red' : o.overall === 'WARN' ? 'amber' : undefined}
          sub={`정상 ${o.summary.OK} · 확인 ${o.summary.WARN} · 조치 ${o.summary.FAIL}`} />
        <Stat label="서버 가동 시간" value={uptime(s.uptimeSec)} sub={`기동 ${fmtTime(s.startedAt)}`} />
        <Stat label="마지막 백업" value={o.backup.lastAt ? ago(o.backup.lastAt) : '없음'} tone={o.checks.find((c) => c.key === 'backup')?.status === 'OK' ? undefined : 'amber'}
          sub={o.backup.dirMounted ? `보관 ${o.backup.count}개` : '백업 폴더 미연결'} />
        <Stat label="디스크 여유" value={`${(s.diskFreeRatio * 100).toFixed(0)}%`} tone={s.diskFreeRatio < 0.05 ? 'red' : s.diskFreeRatio < 0.15 ? 'amber' : undefined}
          sub={`${mb(s.diskFreeBytes)} / ${mb(s.diskTotalBytes)}`} />
      </div>

      <Card title="일일 점검 항목" className="mt-4">
        <Table head={['항목', '판정', '내용', '조치 절차']}>
          {o.checks.map((c) => (
            <tr key={c.key}>
              <td className="py-2 pr-3 font-medium">{c.label}</td>
              <td className="pr-3"><Badge tone={TONE[c.status]}>{LABEL[c.status]}</Badge></td>
              <td className="pr-3 text-sm text-slate-600">{c.detail}</td>
              <td className="whitespace-nowrap pr-3 text-xs text-slate-500">{c.status === 'OK' ? '-' : c.action}</td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-xs text-slate-500">'확인 필요'·'즉시 조치' 항목은 운영 매뉴얼의 해당 절차를 따릅니다. 점검표 CSV를 내려받아 일일 점검 기록으로 보관하세요.</p>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="서버·애플리케이션">
          <dl className="grid grid-cols-[8rem_1fr] gap-y-1.5 text-sm">
            <dt className="text-slate-500">버전</dt><dd>v{s.version}{s.builtAt && <span className="text-xs text-slate-500"> (빌드 {fmtTime(s.builtAt)})</span>}</dd>
            <dt className="text-slate-500">Java · 시간대</dt><dd>{s.java} · {s.timeZone}</dd>
            <dt className="text-slate-500">메모리</dt><dd>{mb(s.memUsedBytes)} / 최대 {mb(s.memMaxBytes)}</dd>
            <dt className="text-slate-500">수신 누계</dt><dd>{Object.entries(o.ingestCounters).map(([k, v]) => `${{ received: '수신', saved: '저장', duplicates: '중복', rejected: '거부' }[k] ?? k} ${v.toLocaleString()}`).join(' · ')}</dd>
            <dt className="text-slate-500">GA4</dt>
            <dd>{gaEnabled() ? <><Badge tone="green">수집 중</Badge> <span className="text-xs text-slate-500">{ga}</span></> : <><Badge>미설정</Badge> <span className="text-xs text-slate-500">.env의 GA_MEASUREMENT_ID 설정 후 프런트엔드 재빌드</span></>}</dd>
          </dl>
        </Card>
        <Card title="데이터베이스·보존">
          <dl className="grid grid-cols-[8rem_1fr] gap-y-1.5 text-sm">
            <dt className="text-slate-500">MySQL</dt><dd>{o.database.version}</dd>
            <dt className="text-slate-500">스키마</dt><dd>{o.database.migration}</dd>
            <dt className="text-slate-500">전체 용량</dt><dd>{mb(o.database.totalBytes)} · 테이블 {o.database.tables.length}개</dd>
            <dt className="text-slate-500">원시 데이터</dt><dd>{o.database.sensorDataRows.toLocaleString()}건 · 가장 오래된 값 {o.retention.oldestRaw === '-' ? '-' : fmtTime(o.retention.oldestRaw)}</dd>
            <dt className="text-slate-500">보존 정책</dt><dd>원시 1분 데이터 {o.retention.rawDays}일 (매일 03:00 삭제) · 시간 집계 영구</dd>
          </dl>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="용량 상위 테이블">
          <Table head={['테이블', '행(추정)', '용량']}>
            {o.database.tables.slice(0, 8).map((t) => (
              <tr key={t.name}><td className="py-1.5 pr-3 text-xs">{t.name}</td><td className="pr-3 text-xs">{Number(t.approxRows).toLocaleString()}</td><td className="pr-3 text-xs">{mb(Number(t.bytes))}</td></tr>
            ))}
          </Table>
        </Card>
        <Card title={`백업 파일 (${o.backup.dir})`}>
          {!o.backup.dirMounted ? <Empty>백업 폴더가 서버에 연결되지 않았습니다. docker-compose.yml의 backend volumes(./backups:/backups:ro)를 확인하세요.</Empty>
            : !o.backup.files.length ? <Empty>백업 파일이 없습니다. tools/backup-db.sh를 실행하고 cron에 등록하세요.</Empty>
              : (
                <Table head={['파일', '크기', '만든 시각']}>
                  {o.backup.files.map((f) => (
                    <tr key={f.file}><td className="py-1.5 pr-3 text-xs">{f.file}</td><td className="pr-3 text-xs">{mb(f.bytes)}</td><td className="whitespace-nowrap pr-3 text-xs">{fmtTime(f.at)}</td></tr>
                  ))}
                </Table>
              )}
        </Card>
      </div>
    </div>
  );
}
