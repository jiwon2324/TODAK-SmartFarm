import { useEffect, useMemo, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { download, get } from '../../api/client';
import type { DailyStat, GddResult, Reading, Series } from '../../api/types';
import { fmtMd, fmtTime, isoDate, isoLocal } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, Empty, ErrorBox, PageTitle, SimNotice, Table } from '../../components/ui';

const RANGES = [{ d: 3, l: '3일' }, { d: 7, l: '7일' }, { d: 14, l: '14일' }, { d: 30, l: '30일' }];

/** SCR-03·08 환경 데이터 분석: 시간별 변화, 일별 통계, 일교차, GDD(내부·외부), CSV [REQ-F-10, F-14, F-15] */
export default function Analytics() {
  const { farmId } = useFarm();
  const [days, setDays] = useState(7);
  const [hourly, setHourly] = useState<Record<string, number | string>[]>([]);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [gIn, setGIn] = useState<GddResult | null>(null);
  const [gEx, setGEx] = useState<GddResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!farmId) return;
    const to = new Date();
    const from = new Date(to.getTime() - days * 86400000);
    (async () => {
      try {
        const sensors = await get<Reading[]>(`/api/sensors?farmId=${farmId}`);
        const pick = sensors.filter((s) => ['TEMP', 'HUMI', 'TEMP_OUT'].includes(s.metric));
        const series = await Promise.all(pick.map((s) =>
          get<Series>(`/api/sensor-data/series?sensorId=${s.sensorId}&from=${isoLocal(from)}&to=${isoLocal(to)}&interval=hour`)));
        const m = new Map<string, Record<string, number | string>>();
        series.forEach((s) => s.points.forEach((p) => {
          const r = m.get(p.t) ?? { t: p.t };
          r[s.sensorCode] = Math.round((p.avg ?? 0) * 10) / 10;
          m.set(p.t, r);
        }));
        setHourly([...m.values()].sort((a, b) => String(a.t).localeCompare(String(b.t))));
        setDaily(await get<DailyStat[]>(`/api/analytics/daily?farmId=${farmId}&from=${isoDate(from)}&to=${isoDate(to)}`));
        setGIn(await get<GddResult>(`/api/analytics/gdd?farmId=${farmId}&source=INTERNAL`));
        setGEx(await get<GddResult>(`/api/analytics/gdd?farmId=${farmId}&source=EXTERNAL`));
        setErr(null);
      } catch (e) {
        setErr((e as Error).message);
      }
    })();
  }, [farmId, days]);

  const gddRows = useMemo(() => {
    if (!gIn) return [];
    const ex = new Map((gEx?.days ?? []).map((d) => [d.date, d]));
    return gIn.days.map((d) => ({ date: d.date, gdd: d.gdd, cum: d.cumGdd, complete: d.complete, exCum: ex.get(d.date)?.cumGdd ?? null }));
  }, [gIn, gEx]);
  const hasExternal = (gEx?.days ?? []).some((d) => d.gdd !== null);
  const hasKma = daily.some((d) => d.kmaTavg !== undefined);
  const last = gIn?.days.filter((d) => d.cumGdd !== null).slice(-1)[0];

  return (
    <div>
      <PageTitle title="환경 데이터 분석" desc="하우스 내부 센서(시간 집계)와 외부 자료를 구분해 보여 줍니다"
        action={<div className="flex gap-1">{RANGES.map((r) => (
          <Button key={r.d} small variant={r.d === days ? 'primary' : 'secondary'} onClick={() => setDays(r.d)}>{r.l}</Button>
        ))}</div>} />
      <SimNotice />
      <ErrorBox msg={err} />

      <Card title="시간별 온도·습도 변화" action={<Button small variant="secondary" onClick={() => {
        const to = new Date();
        download(`/api/sensor-data/export.csv?farmId=${farmId}&from=${isoLocal(new Date(to.getTime() - days * 86400000))}&to=${isoLocal(to)}`, `todak_sensor_${days}d.csv`);
      }}>측정값 CSV</Button>}>
        <div className="h-72">
          <ResponsiveContainer>
            <LineChart data={hourly} margin={{ left: -10, right: 8 }}>
              <CartesianGrid stroke="#eef2f7" />
              <XAxis dataKey="t" tickFormatter={(t) => fmtMd(String(t))} minTickGap={30} fontSize={12} />
              <YAxis yAxisId="t" unit="℃" fontSize={12} />
              <YAxis yAxisId="h" orientation="right" unit="%" fontSize={12} domain={[30, 100]} />
              <Tooltip labelFormatter={(l) => fmtTime(String(l))} />
              <Legend />
              <Line yAxisId="t" dataKey="S-T01" name="내부 온도 Z1" stroke="#2e7d32" dot={false} isAnimationActive={false} />
              <Line yAxisId="t" dataKey="S-T02" name="내부 온도 Z2" stroke="#e65100" dot={false} isAnimationActive={false} />
              <Line yAxisId="t" dataKey="S-TO01" name="하우스 밖 센서" stroke="#64748b" dot={false} strokeDasharray="5 4" isAnimationActive={false} />
              <Line yAxisId="h" dataKey="S-H01" name="습도 Z1" stroke="#1565c0" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="일별 평균·최고·최저 온도와 일교차">
          <div className="h-64">
            <ResponsiveContainer>
              <ComposedChart data={daily} margin={{ left: -10, right: 8 }}>
                <CartesianGrid stroke="#eef2f7" />
                <XAxis dataKey="date" tickFormatter={fmtMd} fontSize={12} />
                <YAxis unit="℃" fontSize={12} />
                <Tooltip />
                <Legend />
                <Bar dataKey="diurnal" name="일교차" fill="#cbd5e1" isAnimationActive={false} />
                <Line dataKey="tempMax" name="최고" stroke="#e65100" isAnimationActive={false} />
                <Line dataKey="tempAvg" name="평균" stroke="#2e7d32" strokeWidth={2} isAnimationActive={false} />
                <Line dataKey="tempMin" name="최저" stroke="#1565c0" isAnimationActive={false} />
                {hasKma && <Line dataKey="kmaTavg" name="기상청 외부 평균" stroke="#7c3aed" strokeDasharray="4 3" isAnimationActive={false} />}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          {!hasKma && <p className="mt-2 text-xs text-slate-500">기상청 양평 ASOS 자료가 아직 없습니다. 관리자 → 외부 기상 자료에서 CSV를 가져오면 외부 평균기온이 함께 표시됩니다.</p>}
        </Card>

        <Card title="유효적산온도(GDD)" action={<div className="flex gap-1">
          <Button small variant="secondary" onClick={() => download(`/api/analytics/gdd/export.csv?farmId=${farmId}&source=INTERNAL`, 'todak_gdd_internal.csv')}>내부 CSV</Button>
          {hasExternal && <Button small variant="secondary" onClick={() => download(`/api/analytics/gdd/export.csv?farmId=${farmId}&source=EXTERNAL`, 'todak_gdd_external.csv')}>외부 CSV</Button>}
        </div>}>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <span>정식 {gIn?.transplantDate} 이후 누적</span>
            <span className="text-xl font-bold text-leaf-700">{last?.cumGdd ?? '-'} ℃·일</span>
            <Badge>기준 {gIn?.base}℃ · 상한 {gIn?.upper}℃</Badge>
          </div>
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

      <Card title="일별 통계표" className="mt-4">
        {daily.length === 0 ? <Empty>자료 없음</Empty> : (
          <Table head={['날짜', '평균', '최고', '최저', '일교차', '평균 습도', 'DLI 추정', '하우스 밖 센서', '기상청 평균']}>
            {[...daily].reverse().map((r) => (
              <tr key={r.date}>
                <td className="py-1.5 pr-3">{r.date}</td>
                <td className="pr-3">{r.tempAvg ?? '-'}</td>
                <td className="pr-3">{r.tempMax ?? '-'}</td>
                <td className="pr-3">{r.tempMin ?? '-'}</td>
                <td className="pr-3">{r.diurnal ?? '-'}</td>
                <td className="pr-3">{r.humiAvg ?? '-'}</td>
                <td className="pr-3">{r.dliEstimate ?? '-'}</td>
                <td className="pr-3">{r.outSensorAvg ?? '-'}</td>
                <td className="pr-3">{r.kmaTavg ?? '-'}</td>
              </tr>
            ))}
          </Table>
        )}
        <p className="mt-2 text-xs text-slate-500">단위 ℃, %, DLI는 mol·m⁻²·d⁻¹ (일사량 × 2.02 µmol/J 환산 추정치). 하우스 밖 센서와 기상청 평균은 출처가 다른 별개의 값입니다.</p>
      </Card>
    </div>
  );
}
