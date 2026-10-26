import { useCallback, useEffect, useState } from 'react';
import { get, patch, post } from '../../api/client';
import type { CropCycle, CropStd } from '../../api/types';
import { STAGE_LABEL, fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { StdForm } from '../../components/StdForm';
import { useReadOnly } from '../../hooks/auth';
import { Badge, Button, Card, ErrorBox, Field, PageTitle, Table, inputCls } from '../../components/ui';

interface Hive {
  hiveId: number;
  placedDate: string;
  replaceDays: number;
  removedDate: string | null;
}

/** SCR-07·08 재배 관리: 생육 단계·정식일·GDD 기준, 단계별 환경 기준(버전), 벌통 교체 [REQ-F-06, F-11, F-14] */
export default function Crop() {
  const { farmId } = useFarm();
  const [cycle, setCycle] = useState<CropCycle | null>(null);
  const [stds, setStds] = useState<{ current: CropStd[]; all: CropStd[] } | null>(null);
  const [hives, setHives] = useState<Hive[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [form, setForm] = useState({ stage: '', transplantDate: '', gddBaseC: '', gddUpperC: '' });
  const readOnly = useReadOnly();
  const [hive, setHive] = useState({ placedDate: new Date().toISOString().slice(0, 10), replaceDays: 6 });

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const c = await get<CropCycle>(`/api/crop-cycles/current?farmId=${farmId}`);
      setCycle(c);
      setForm({ stage: c.currentStage, transplantDate: c.transplantDate, gddBaseC: String(c.gddBaseC), gddUpperC: String(c.gddUpperC) });
      setStds(await get(`/api/crop-standards?farmId=${farmId}`));
      setHives(await get<Hive[]>(`/api/beehives?farmId=${farmId}`));
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
      setMsg('작기 정보를 저장했습니다. 바뀐 생육 단계 기준이 자동 제어에 적용됩니다.');
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

  const active = hives.find((h) => !h.removedDate);
  const due = active ? new Date(new Date(active.placedDate).getTime() + active.replaceDays * 86400000).toISOString().slice(0, 10) : null;

  return (
    <div>
      <PageTitle title="재배 관리" desc="방울토마토 생육 단계와 단계별 환경 기준, 수정(벌통)과 수확 관련 정보" />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="현재 작기">
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

        <Card title="수확 적기 판단">
          <Badge tone="amber">확장 기능 · 미구현</Badge>
          <p className="mt-3 text-sm text-slate-600">카메라 착색도 분석(REQ-F-07)은 학습·검증용 이미지(라벨 300장 이상)를 확보한 뒤 구현할 확장 기능입니다. 현재 버전에는 포함되지 않았으며, 수확은 농가가 직접 판단합니다.</p>
        </Card>
      </div>

      <Card title="생육 단계별 환경 기준 (현재 버전)" className="mt-4">
        <Table head={['단계', '버전', '주간 온도', '야간 온도', '습도', 'EC', 'pH', '배지수분 하한', '근거', '적용']}>
          {(stds?.current ?? []).map((s) => (
            <tr key={s.stdId} className={s.stage === cycle?.currentStage ? 'bg-leaf-50' : ''}>
              <td className="py-1.5 pr-3">{STAGE_LABEL[s.stage]}{s.stage === cycle?.currentStage && ' ●'}</td>
              <td className="pr-3">v{s.versionNo}</td>
              <td className="pr-3">{s.dayTempMin}~{s.dayTempMax}℃</td>
              <td className="pr-3">{s.nightTempMin}~{s.nightTempMax}℃</td>
              <td className="pr-3">{s.humidityMin}~{s.humidityMax}%</td>
              <td className="pr-3">{s.ecMin}~{s.ecMax}</td>
              <td className="pr-3">{s.phMin}~{s.phMax}</td>
              <td className="pr-3">{s.substrateMoistureMin ?? '-'}%</td>
              <td className="pr-3 text-xs text-slate-500">{s.sourceNote}</td>
              <td className="whitespace-nowrap pr-3 text-xs">{fmtTime(s.effectiveFrom)}</td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-xs text-slate-500">근거: 개발 계획서 4.3절 (S4 농진청 야간 15℃·습도 70~80%, S5 생육 단계별 EC, S6 야간온도 연구, S9 농사로). 바꾸면 덮어쓰지 않고 새 버전으로 쌓입니다.</p>
      </Card>

      <Card title="단계별 환경 기준 새 버전 등록 (UC-05)" className="mt-4">
        {farmId && <StdForm farmId={farmId} current={stds?.current ?? []} initialStage={cycle?.currentStage} disabled={readOnly}
          onSaved={(m) => { setMsg(m); setErr(null); load(); }} onError={setErr} />}
      </Card>
    </div>
  );
}
