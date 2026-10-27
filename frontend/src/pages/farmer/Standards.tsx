import { useCallback, useEffect, useState } from 'react';
import { get } from '../../api/client';
import type { ControlRule, CropCycle, CropStd } from '../../api/types';
import { METRIC_LABEL, STAGE_LABEL, fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { StdForm } from '../../components/StdForm';
import { Badge, Card, ErrorBox, Notice, PageTitle, Table } from '../../components/ui';
import { useReadOnly } from '../../hooks/auth';

/** SCR-07 재배 기준값·제어 규칙: 생육 단계별 기준 버전(조회·새 버전 등록), 자동 제어 규칙 임계값(조회) [REQ-F-02~04, F-11] */
export default function Standards() {
  const { farmId } = useFarm();
  const readOnly = useReadOnly();
  const [cycle, setCycle] = useState<CropCycle | null>(null);
  const [stds, setStds] = useState<{ current: CropStd[]; all: CropStd[] } | null>(null);
  const [rules, setRules] = useState<ControlRule[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      const [c, s, r] = await Promise.all([
        get<CropCycle>(`/api/crop-cycles/current?farmId=${farmId}`),
        get<{ current: CropStd[]; all: CropStd[] }>(`/api/crop-standards?farmId=${farmId}`),
        get<ControlRule[]>(`/api/controls/rules?farmId=${farmId}`),
      ]);
      setCycle(c);
      setStds(s);
      setRules(r);
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);
  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <PageTitle title="재배 기준값 · 제어 규칙" desc={`현재 생육 단계: ${cycle ? STAGE_LABEL[cycle.currentStage] : '-'} · 기준값은 덮어쓰지 않고 새 버전으로 쌓이며 저장 즉시 현장 게이트웨이에 사본이 전달됩니다`} />
      <ErrorBox msg={err} />
      <Notice tone="ok">{msg}</Notice>
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
              <td className="pr-3 text-xs text-slate-600">{s.sourceNote}</td>
              <td className="whitespace-nowrap pr-3 text-xs">{fmtTime(s.effectiveFrom)}</td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-xs text-slate-500">근거: 개발 계획서 4.3절 (S4 농진청 야간 15℃·습도 70~80%, S5 생육 단계별 EC, S6 야간온도 연구, S9 농사로). 바꾸면 덮어쓰지 않고 새 버전으로 쌓입니다.</p>
      </Card>


      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="단계별 기준값 새 버전 등록 (UC-05)">
          {farmId && <StdForm farmId={farmId} current={stds?.current ?? []} initialStage={cycle?.currentStage} disabled={readOnly}
            onSaved={(m) => { setMsg(m); setErr(null); load(); }} onError={setErr} />}
        </Card>
        <Card title="기준값 버전 이력" className="xl:col-span-2">
          <Table head={['단계', '버전', '주간', '야간', '습도', 'EC', 'pH', '적용 시작', '']}>
            {(stds?.all ?? []).map((s) => (
              <tr key={s.stdId}>
                <td className="py-1.5 pr-3">{STAGE_LABEL[s.stage]}</td><td className="pr-3">v{s.versionNo}</td>
                <td className="pr-3">{s.dayTempMin}~{s.dayTempMax}</td><td className="pr-3">{s.nightTempMin}~{s.nightTempMax}</td>
                <td className="pr-3">{s.humidityMin}~{s.humidityMax}</td><td className="pr-3">{s.ecMin}~{s.ecMax}</td><td className="pr-3">{s.phMin}~{s.phMax}</td>
                <td className="whitespace-nowrap pr-3 text-xs">{fmtTime(s.effectiveFrom)}</td><td>{s.isCurrent && <Badge tone="green">현재</Badge>}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>

      <Card title="자동 제어 규칙 (임계값은 관리자만 변경)" className="mt-4">
        <Table head={['규칙', '이름', '조건', '해제', '대상', '시간대', '구분']}>
          {rules.filter((r) => r.isEnabled).map((r) => (
            <tr key={r.ruleId}>
              <td className="py-1.5 pr-3 font-medium">{r.ruleCode}</td>
              <td className="pr-3">{r.ruleName}</td>
              <td className="pr-3">{METRIC_LABEL[r.metric]} {r.compareOp === 'GE' ? '≥' : '≤'} {r.onThreshold}</td>
              <td className="pr-3">{r.offThreshold}</td>
              <td className="pr-3">{r.targetDeviceType}{r.stage2DeviceType ? ` → ${r.stage2DeviceType}` : ''}</td>
              <td className="pr-3">{{ DAY: '주간', NIGHT: '야간', ALL: '종일' }[r.period]}</td>
              <td className="pr-3">{r.isSafety ? <Badge tone="red">안전 한계</Badge> : '자동'}</td>
            </tr>
          ))}
        </Table>
        <p className="mt-2 text-xs text-slate-500">작동값과 해제값을 다르게 둬 임계값 근처에서 켜졌다 꺼졌다를 반복하지 않습니다(히스테리시스). 값 변경은 관리자만 할 수 있습니다.</p>
      </Card>
    </div>
  );
}
