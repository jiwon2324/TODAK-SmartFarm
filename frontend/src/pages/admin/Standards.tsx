import { useCallback, useEffect, useState } from 'react';
import { get, patch, post } from '../../api/client';
import type { ControlRule, CropStd } from '../../api/types';
import { METRIC_LABEL, STAGE_LABEL, fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, ErrorBox, Field, PageTitle, Table, inputCls } from '../../components/ui';

const NUM_FIELDS: [keyof CropStd, string][] = [
  ['dayTempMin', '주간 최저℃'], ['dayTempMax', '주간 최고℃'], ['nightTempMin', '야간 최저℃'], ['nightTempMax', '야간 최고℃'],
  ['humidityMin', '습도 최저%'], ['humidityMax', '습도 최고%'], ['ecMin', 'EC 최저'], ['ecMax', 'EC 최고'],
  ['phMin', 'pH 최저'], ['phMax', 'pH 최고'], ['substrateMoistureMin', '배지수분 하한%'],
];

/** SCR-07 재배 기준값(버전 관리)·자동 제어 규칙(히스테리시스) 관리 [REQ-F-02~04, F-11] */
export default function Standards() {
  const { farmId } = useFarm();
  const [stds, setStds] = useState<{ current: CropStd[]; all: CropStd[] } | null>(null);
  const [rules, setRules] = useState<ControlRule[]>([]);
  const [stage, setStage] = useState('GROWTH');
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [note, setNote] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const s = await get<{ current: CropStd[]; all: CropStd[] }>(`/api/crop-standards?farmId=${farmId}`);
      setStds(s);
      setRules(await get<ControlRule[]>(`/api/admin/rules?farmId=${farmId}`));
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);
  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const cur = stds?.current.find((x) => x.stage === stage);
    if (cur) {
      setDraft(Object.fromEntries(NUM_FIELDS.map(([k]) => [k, String(cur[k] ?? '')])));
      setNote(cur.sourceNote ?? '');
    }
  }, [stds, stage]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      setMsg(ok);
      setErr(null);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const saveStd = () => act(() => post('/api/crop-standards', {
    farmId, stage, sourceNote: note, ...Object.fromEntries(NUM_FIELDS.map(([k]) => [k, draft[k as string] === '' ? null : Number(draft[k as string])])),
  }), '새 버전을 저장하고 현장 게이트웨이에 기준값 사본을 다시 보냈습니다.');

  const editRule = (r: ControlRule, field: 'onThreshold' | 'offThreshold') => {
    const v = window.prompt(`${r.ruleCode} ${field === 'onThreshold' ? '작동값' : '해제값'}`, String(r[field]));
    if (v !== null) act(() => patch(`/api/admin/rules/${r.ruleId}`, { [field]: Number(v) }), `${r.ruleCode} 규칙을 수정했습니다.`);
  };

  return (
    <div>
      <PageTitle title="재배 기준값 · 자동 제어 규칙" desc="기준값은 덮어쓰지 않고 새 버전으로 쌓입니다. 규칙은 히스테리시스 방향(작동값/해제값)을 검사합니다." />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="생육 단계별 기준 — 새 버전 등록">
          <Field label="생육 단계">
            <select className={inputCls} value={stage} onChange={(e) => setStage(e.target.value)}>
              {Object.entries(STAGE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {NUM_FIELDS.map(([k, l]) => (
              <Field key={k} label={l}><input type="number" step="0.1" className={inputCls} value={draft[k as string] ?? ''}
                onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} /></Field>
            ))}
          </div>
          <div className="mt-2"><Field label="근거 출처"><input className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} /></Field></div>
          <div className="mt-3"><Button onClick={saveStd}>새 버전 저장</Button></div>
        </Card>
        <Card title="기준값 버전 이력" className="xl:col-span-2">
          <Table head={['단계', '버전', '주간', '야간', '습도', 'EC', 'pH', '적용 시작', '현재']}>
            {(stds?.all ?? []).map((s) => (
              <tr key={s.stdId}>
                <td className="py-1.5 pr-3">{STAGE_LABEL[s.stage]}</td>
                <td className="pr-3">v{s.versionNo}</td>
                <td className="pr-3">{s.dayTempMin}~{s.dayTempMax}</td>
                <td className="pr-3">{s.nightTempMin}~{s.nightTempMax}</td>
                <td className="pr-3">{s.humidityMin}~{s.humidityMax}</td>
                <td className="pr-3">{s.ecMin}~{s.ecMax}</td>
                <td className="pr-3">{s.phMin}~{s.phMax}</td>
                <td className="whitespace-nowrap pr-3 text-xs">{fmtTime(s.effectiveFrom)}</td>
                <td>{s.isCurrent && <Badge tone="green">현재</Badge>}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>

      <Card title="자동 제어 규칙" className="mt-4">
        <Table head={['규칙', '이름', '지표', '시간대', '작동', '해제', '대상', '최소 작동', '관수 상한', '안전', '사용']}>
          {rules.map((r) => (
            <tr key={r.ruleId}>
              <td className="py-2 pr-3 font-medium">{r.ruleCode}</td>
              <td className="pr-3">{r.ruleName}</td>
              <td className="pr-3">{METRIC_LABEL[r.metric]}</td>
              <td className="pr-3">{{ DAY: '주간', NIGHT: '야간', ALL: '종일' }[r.period]}</td>
              <td className="pr-3"><button className="text-leaf-700 underline" onClick={() => editRule(r, 'onThreshold')}>{r.compareOp === 'GE' ? '≥' : '≤'} {r.onThreshold}</button></td>
              <td className="pr-3"><button className="text-leaf-700 underline" onClick={() => editRule(r, 'offThreshold')}>{r.offThreshold}</button></td>
              <td className="pr-3">{r.targetDeviceType}</td>
              <td className="pr-3">{r.minRunSec}초</td>
              <td className="pr-3 text-xs">{r.maxRunSec ? `1회 ${r.maxRunSec}초 · 일 ${r.maxDailyCount}회` : '-'}</td>
              <td className="pr-3">{r.isSafety && <Badge tone="red">안전</Badge>}</td>
              <td><input type="checkbox" checked={r.isEnabled} onChange={() => act(() => patch(`/api/admin/rules/${r.ruleId}`, { isEnabled: !r.isEnabled }), `${r.ruleCode} 사용 여부를 바꿨습니다.`)} /></td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-xs text-slate-500">안전 규칙(CR-05 고온 35℃, CR-06 저온 5℃)은 수동 모드보다 우선하며, 통신이 끊기면 현장 게이트웨이가 같은 규칙 사본으로 동작합니다.</p>
      </Card>
    </div>
  );
}
