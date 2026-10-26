import { useEffect, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { download, get } from '../../api/client';
import type { DailyStat, Reading, Series } from '../../api/types';
import { METRIC_LABEL, fmtMd, fmtTime, isoDate, isoLocal, unit } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Button, Card, Empty, ErrorBox, PageTitle, SimNotice, Table } from '../../components/ui';

const RANGES = [{ d: 3, l: '3일' }, { d: 7, l: '7일' }, { d: 14, l: '14일' }, { d: 30, l: '30일' }];

/** SCR-03 환경 그래프: 기간·지표·집계 선택, 시간별 변화, 일별 통계·일교차·DIF·DLI, CSV [REQ-F-10] */
export default function Graph() {
  const { farmId } = useFarm();
  const [days, setDays] = useState(7);
  const [hourly, setHourly] = useState<Record<string, number | string>[]>([]);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [metric, setMetric] = useState('CO2');
  const [interval, setIntervalKind] = useState<'raw' | 'hour'>('hour');
  const [mSeries, setMSeries] = useState<{ rows: Record<string, number | string>[]; codes: string[]; unit: string }>({ rows: [], codes: [], unit: '' });

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
        setErr(null);
      } catch (e) {
        setErr((e as Error).message);
      }
    })();
  }, [farmId, days]);

  // SCR-03: 지표·집계 단위를 골라 조회 (원시 1분은 최대 3일만 화면에 그림)
  useEffect(() => {
    if (!farmId) return;
    const to = new Date();
    const span = interval === 'raw' ? Math.min(days, 3) : days;
    const from = new Date(to.getTime() - span * 86400000);
    (async () => {
      try {
        const sensors = (await get<Reading[]>(`/api/sensors?farmId=${farmId}`)).filter((x) => x.metric === metric);
        const series = await Promise.all(sensors.map((x) =>
          get<Series>(`/api/sensor-data/series?sensorId=${x.sensorId}&from=${isoLocal(from)}&to=${isoLocal(to)}&interval=${interval}`)));
        const m = new Map<string, Record<string, number | string>>();
        series.forEach((x) => x.points.forEach((p) => {
          const r = m.get(p.t) ?? { t: p.t };
          r[x.sensorCode] = (interval === 'raw' ? p.value : p.avg) as number;
          m.set(p.t, r);
        }));
        setMSeries({ rows: [...m.values()].sort((a, b) => String(a.t).localeCompare(String(b.t))), codes: series.map((x) => x.sensorCode), unit: sensors[0]?.unit ?? '' });
      } catch (e) {
        setErr((e as Error).message);
      }
    })();
  }, [farmId, days, metric, interval]);

  const hasKma = daily.some((d) => d.kmaTavg !== undefined);

  return (
    <div>
      <PageTitle title="환경 그래프" desc="기간·지표·집계 단위를 골라 하우스 환경 변화를 봅니다. 내부 센서와 외부 자료는 구분해 표시합니다"
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

      <Card className="mt-4" title="지표별 기간 조회" action={<div className="flex flex-wrap items-center gap-1">
        <select aria-label="지표" className="rounded-lg border border-slate-300 px-2 py-1 text-sm" value={metric} onChange={(e) => setMetric(e.target.value)}>
          {Object.entries(METRIC_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <Button small variant={interval === 'hour' ? 'primary' : 'secondary'} onClick={() => setIntervalKind('hour')}>시간 평균</Button>
        <Button small variant={interval === 'raw' ? 'primary' : 'secondary'} onClick={() => setIntervalKind('raw')}>1분 원시</Button>
      </div>}>
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={mSeries.rows} margin={{ left: -10, right: 8 }}>
              <CartesianGrid stroke="#eef2f7" />
              <XAxis dataKey="t" tickFormatter={(t) => (interval === 'raw' ? fmtTime(String(t)).slice(-5) : fmtMd(String(t)))} minTickGap={30} fontSize={12} />
              <YAxis fontSize={12} unit={unit(mSeries.unit)} domain={['auto', 'auto']} />
              <Tooltip labelFormatter={(l) => fmtTime(String(l))} />
              <Legend />
              {mSeries.codes.map((c, i) => <Line key={c} dataKey={c} stroke={['#2e7d32', '#e65100', '#1565c0', '#7c3aed'][i % 4]} dot={false} isAnimationActive={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-slate-500">{interval === 'raw' ? '1분 원시값은 화면에서 최근 최대 3일만 그립니다(서버는 최대 90일).' : `최근 ${days}일 시간 평균.`} 위 기간 버튼과 함께 바뀝니다.</p>
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

        <Card title="일적산광량(DLI) 추정">
          <div className="h-64">
            <ResponsiveContainer>
              <ComposedChart data={daily} margin={{ left: -10, right: 8 }}>
                <CartesianGrid stroke="#eef2f7" />
                <XAxis dataKey="date" tickFormatter={fmtMd} fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="dliEstimate" name="DLI (mol·m⁻²·d⁻¹)" fill="#f9a825" isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">하우스 안 일사량 시간 평균 합 × 3600 × 2.02 µmol/J로 환산한 추정치입니다. 오늘 값은 진행 중입니다.</p>
        </Card>
      </div>

      <Card title="일별 통계표" className="mt-4">
        {daily.length === 0 ? <Empty>자료 없음</Empty> : (
          <Table head={['날짜', '평균', '최고', '최저', '일교차', 'DIF(주−야)', '평균 습도', 'DLI 추정', '하우스 밖 센서', '기상청 평균']}>
            {[...daily].reverse().map((r) => (
              <tr key={r.date}>
                <td className="py-1.5 pr-3">{r.date}</td>
                <td className="pr-3">{r.tempAvg ?? '-'}</td>
                <td className="pr-3">{r.tempMax ?? '-'}</td>
                <td className="pr-3">{r.tempMin ?? '-'}</td>
                <td className="pr-3">{r.diurnal ?? '-'}</td>
                <td className="pr-3">{r.dif ?? '-'}</td>
                <td className="pr-3">{r.humiAvg ?? '-'}</td>
                <td className="pr-3">{r.dliEstimate ?? '-'}</td>
                <td className="pr-3">{r.outSensorAvg ?? '-'}</td>
                <td className="pr-3">{r.kmaTavg ?? '-'}</td>
              </tr>
            ))}
          </Table>
        )}
        <p className="mt-2 text-xs text-slate-500">DIF는 주간(07~19시) 평균에서 야간 평균을 뺀 값입니다. 단위 ℃, %, DLI는 mol·m⁻²·d⁻¹ (일사량 × 2.02 µmol/J 환산 추정치). 하우스 밖 센서와 기상청 평균은 출처가 다른 별개의 값입니다.</p>
      </Card>

    </div>
  );
}
