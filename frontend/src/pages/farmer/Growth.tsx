import { useCallback, useEffect, useMemo, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { download, get, patch, post } from '../../api/client';
import type { CropCycle, GddResult } from '../../api/types';
import { STAGE_LABEL, fmtMd, isoDate } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, Empty, ErrorBox, Field, Notice, PageTitle, SimNotice, Table, inputCls } from '../../components/ui';
import { useReadOnly } from '../../hooks/auth';

interface Hive {
  hiveId: number;
  placedDate: string;
  replaceDays: number;
  removedDate: string | null;
}

interface Weather {
  obsDate: string;
  tavgC: number | null;
  tminC: number | null;
  tmaxC: number | null;
  rainMm: number | null;
  missingFlags: string | null;
}

/** SCR-08 생육 분석: 내부·외부 GDD, 정식일·기준·상한 온도, 외부 기상 자료, 벌통 [REQ-F-06, F-14, F-15] */
export default function Growth() {
  const { farmId } = useFarm();
  const readOnly = useReadOnly();
  const [gIn, setGIn] = useState<GddResult | null>(null);
  const [gEx, setGEx] = useState<GddResult | null>(null);
  const [cycle, setCycle] = useState<CropCycle | null>(null);
  const [hives, setHives] = useState<Hive[]>([]);
  const [weather, setWeather] = useState<Weather[]>([]);
  const [form, setForm] = useState({ stage: '', transplantDate: '', gddBaseC: '', gddUpperC: '' });
  const [hive, setHive] = useState({ placedDate: new Date().toISOString().slice(0, 10), replaceDays: 6 });
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const to = new Date();
      const [gi, ge, c, h, w] = await Promise.all([
        get<GddResult>(`/api/analytics/gdd?farmId=${farmId}&source=INTERNAL`),
        get<GddResult>(`/api/analytics/gdd?farmId=${farmId}&source=EXTERNAL`),
        get<CropCycle>(`/api/crop-cycles/current?farmId=${farmId}`),
        get<Hive[]>(`/api/beehives?farmId=${farmId}`),
        get<Weather[]>(`/api/analytics/weather?farmId=${farmId}&from=${isoDate(new Date(to.getTime() - 60 * 86400000))}&to=${isoDate(to)}`),
      ]);
      setGIn(gi);
      setGEx(ge);
      setCycle(c);
      setForm({ stage: c.currentStage, transplantDate: c.transplantDate, gddBaseC: String(c.gddBaseC), gddUpperC: String(c.gddUpperC) });
      setHives(h);
      setWeather(w);
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);
  useEffect(() => {
    load();
  }, [load]);

  const saveCycle = async () => {
    if (!cycle) return;
    try {
      if (Number(form.gddUpperC) <= Number(form.gddBaseC)) {
        setErr('상한온도는 기준온도보다 높아야 합니다.');
        return;
      }
      await patch(`/api/crop-cycles/${cycle.cycleId}`, { currentStage: form.stage, transplantDate: form.transplantDate, gddBaseC: Number(form.gddBaseC), gddUpperC: Number(form.gddUpperC) });
      setMsg('작기 정보를 저장했습니다. GDD는 새 기준으로 다시 계산되고, 바뀐 생육 단계 기준이 자동 제어에 적용됩니다.');
      setErr(null);
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const addHive = async () => {
    try {
      await post('/api/beehives', { farmId, ...hive });
      setMsg('벌통을 등록했습니다. 교체 예정일 하루 전에 알림이 옵니다.');
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const gddRows = useMemo(() => {
    if (!gIn) return [];
    const ex = new Map((gEx?.days ?? []).map((d) => [d.date, d]));
    return gIn.days.map((d) => ({ date: d.date, gdd: d.gdd, cum: d.cumGdd, complete: d.complete, exCum: ex.get(d.date)?.cumGdd ?? null }));
  }, [gIn, gEx]);
  const hasExternal = (gEx?.days ?? []).some((d) => d.gdd !== null);
  const last = gIn?.days.filter((d) => d.cumGdd !== null).slice(-1)[0];
  const active = hives.find((h) => !h.removedDate);
  const due = active ? new Date(new Date(active.placedDate).getTime() + active.replaceDays * 86400000).toISOString().slice(0, 10) : null;

  return (
    <div>
      <PageTitle title="생육 분석" desc="정식일부터 쌓인 유효적산온도(GDD)를 하우스 내부 센서와 기상청 외부 자료로 따로 계산해 비교합니다" />
      <SimNotice />
      <ErrorBox msg={err} />
      <Notice tone="ok">{msg}</Notice>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card title="유효적산온도(GDD)" action={<div className="flex gap-1">
          <Button small variant="secondary" onClick={() => download(`/api/analytics/gdd/export.csv?farmId=${farmId}&source=INTERNAL`, 'todak_gdd_internal.csv')}>내부 CSV</Button>
          {hasExternal && <Button small variant="secondary" onClick={() => download(`/api/analytics/gdd/export.csv?farmId=${farmId}&source=EXTERNAL`, 'todak_gdd_external.csv')}>외부 CSV</Button>}
        </div>}>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <span>정식 {gIn?.transplantDate} 이후 누적</span>
            <span className="text-xl font-bold text-leaf-700">{last?.cumGdd ?? '-'} ℃·일</span>
            <Badge>기준 {gIn?.base}℃ · 상한 {gIn?.upper}℃</Badge>
          </div>
          {gIn?.summary && (
            <div className="mb-2 flex flex-wrap gap-1.5 text-xs">
              <Badge tone="blue">정식 후 {gIn.summary.elapsedDays}일</Badge>
              <Badge tone={gIn.summary.missingDays ? 'amber' : 'gray'}>결측 {gIn.summary.missingDays}일</Badge>
              <Badge tone={gIn.summary.incompleteDays ? 'amber' : 'gray'}>불완전(수집률 80% 미만) {gIn.summary.incompleteDays}일</Badge>
              <Badge tone={gIn.summary.hot35Days ? 'red' : 'gray'}>최고 35℃ 이상 {gIn.summary.hot35Days}일</Badge>
              <Badge tone={gIn.summary.cold5Days ? 'red' : 'gray'}>최저 5℃ 이하 {gIn.summary.cold5Days}일</Badge>
            </div>
          )}
          <div className="h-56">
            <ResponsiveContainer>
              <ComposedChart data={gddRows} margin={{ left: -10, right: 8 }}>
                <CartesianGrid stroke="#eef2f7" />
                <XAxis dataKey="date" tickFormatter={fmtMd} fontSize={12} />
                <YAxis yAxisId="d" fontSize={12} />
                <YAxis yAxisId="c" orientation="right" fontSize={12} />
                <Tooltip />
                <Legend />
                <Bar yAxisId="d" dataKey="gdd" name="일 GDD (내부)" fill="#a5d6a7" isAnimationActive={false} />
                <Line yAxisId="c" dataKey="cum" name="누적 (내부)" stroke="#2e7d32" strokeWidth={2} isAnimationActive={false} />
                {hasExternal && <Line yAxisId="c" dataKey="exCum" name="누적 (기상청 외부)" stroke="#7c3aed" strokeDasharray="4 3" isAnimationActive={false} />}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">GDD = max(0, min(일평균, 상한) − 기준온도). 내부는 센서 시간 평균, 외부는 기상청 (최고+최저)/2. 수확일 예측이 아닌 생육 참고 지표입니다.</p>
        </Card>
        </div>
        <Card title="작기 · GDD 계산 기준 (API-20)">
          {cycle && (
            <fieldset disabled={readOnly} className="space-y-3">
              <div className="text-sm text-slate-500">{cycle.variety}</div>
              <Field label="생육 단계">
                <select className={inputCls} value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })}>
                  {Object.entries(STAGE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </Field>
              <Field label="정식일 (GDD 누적 시작)">
                <input type="date" className={inputCls} value={form.transplantDate} onChange={(e) => setForm({ ...form, transplantDate: e.target.value })} />
              </Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="GDD 기준온도 ℃ (문헌 10)">
                  <input type="number" step="0.5" className={inputCls} value={form.gddBaseC} onChange={(e) => setForm({ ...form, gddBaseC: e.target.value })} />
                </Field>
                <Field label="상한온도 ℃ (문헌 30)">
                  <input type="number" step="0.5" className={inputCls} value={form.gddUpperC} onChange={(e) => setForm({ ...form, gddUpperC: e.target.value })} />
                </Field>
              </div>
              <Button onClick={saveCycle} disabled={readOnly}>저장</Button>
              <p className="text-xs text-slate-500">변경 내역은 설정 이력에 남고, GDD는 새 기준으로 다시 계산됩니다.</p>
            </fieldset>
          )}
        </Card>

      </div>

      <Card title="일별 GDD 표 (정식일부터)" className="mt-4">
        {!gIn ? <Empty>자료 없음</Empty> : (
          <Table head={['날짜', '일평균(내부)', '일 GDD', '누적 GDD', '수집률', '상태', '외부 누적(기상청)']}>
            {[...gIn.days].reverse().map((d) => {
              const ex = gEx?.days.find((x) => x.date === d.date);
              return (
                <tr key={d.date} className={!d.complete ? 'bg-amber-50' : ''}>
                  <td className="py-1.5 pr-3">{d.date}</td>
                  <td className="pr-3">{d.tavg ?? '-'}</td>
                  <td className="pr-3">{d.gdd ?? '-'}</td>
                  <td className="pr-3 font-medium">{d.cumGdd ?? '-'}</td>
                  <td className="pr-3">{d.coverage}%</td>
                  <td className="pr-3">{d.gdd === null ? <Badge tone="red">결측</Badge> : d.complete ? <Badge tone="green">완전</Badge> : <Badge tone="amber">불완전</Badge>}</td>
                  <td className="pr-3">{ex?.cumGdd ?? '-'}</td>
                </tr>
              );
            })}
          </Table>
        )}
        <p className="mt-2 text-xs text-slate-500">수집률 80% 미만인 날은 '불완전'으로 표시하고 계산은 하되 참고만 합니다. 하루 전체 결측이면 GDD를 비워 두고 누적은 직전 값을 유지합니다 (계획서 알고리즘 5-1).</p>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="외부 기상 자료 (기상청 양평 ASOS, 최근 60일)" className="lg:col-span-2">
          {weather.length === 0 ? <Empty>아직 가져온 기상청 자료가 없습니다. 관리자가 기상자료개방포털 CSV를 올리면 표시됩니다 (시뮬레이션 값으로 채우지 않음).</Empty> : (
            <Table head={['날짜', '평균', '최저', '최고', '강수(mm)', '결측']}>
              {[...weather].reverse().map((w) => (
                <tr key={w.obsDate}>
                  <td className="py-1.5 pr-3">{w.obsDate}</td><td className="pr-3">{w.tavgC ?? '-'}</td><td className="pr-3">{w.tminC ?? '-'}</td>
                  <td className="pr-3">{w.tmaxC ?? '-'}</td><td className="pr-3">{w.rainMm ?? '-'}</td><td className="pr-3 text-xs text-red-700">{w.missingFlags}</td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
        <Card title="수정 — 뒤영벌 벌통">
          {active ? (
            <div className="mb-3 rounded-lg bg-slate-50 p-3 text-sm">
              <div>투입일 {active.placedDate} · 교체 주기 {active.replaceDays}일</div>
              <div className="mt-1 font-semibold">교체 예정일 {due}</div>
            </div>
          ) : <div className="mb-3 text-sm text-slate-500">등록된 벌통 없음</div>}
          <div className="grid grid-cols-2 gap-2">
            <Field label="새 벌통 투입일"><input type="date" className={inputCls} value={hive.placedDate} onChange={(e) => setHive({ ...hive, placedDate: e.target.value })} /></Field>
            <Field label="교체 주기(일)"><input type="number" min={1} max={60} className={inputCls} value={hive.replaceDays} onChange={(e) => setHive({ ...hive, replaceDays: Number(e.target.value) })} /></Field>
          </div>
          <div className="mt-3"><Button variant="secondary" onClick={addHive} disabled={readOnly}>벌통 교체 등록</Button></div>
          <p className="mt-2 text-xs text-slate-500">벌 활동 자체는 측정하지 않습니다. 교체 시기 알림과 개화기 고온·다습 경고로 수정을 돕습니다(의사결정 지원).</p>
        </Card>

      </div>
    </div>
  );
}
