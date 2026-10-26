import { FormEvent, useCallback, useEffect, useState } from 'react';
import { get, patch, post } from '../../api/client';
import type { DeviceView, Sensor, Zone } from '../../api/types';
import { METRIC_LABEL, STATE_LABEL, ago, unit } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, ErrorBox, Field, PageTitle, Table, inputCls } from '../../components/ui';

interface IngestRow {
  sensorId: number;
  sensorCode: string;
  receivedLastHour: number;
  expectedPerHour: number;
}

/** SCR-A3 센서·장치 관리: 등록·수정, 설치 위치, 상태, 수집 주기(최근 1시간 수신률) [REQ-F-13] */
export default function Equipment() {
  const { farmId } = useFarm();
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [devices, setDevices] = useState<DeviceView[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [ingest, setIngest] = useState<Record<number, IngestRow>>({});
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [nf, setNf] = useState({ sensorCode: '', metric: 'TEMP', unit: 'C', zoneId: 0, validMin: -20, validMax: 60, installNote: '' });

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      setSensors(await get<Sensor[]>(`/api/sensors?farmId=${farmId}`));
      setDevices(await get<DeviceView[]>(`/api/devices?farmId=${farmId}`));
      setZones(await get<Zone[]>(`/api/farms/${farmId}/zones`));
      const lg = await get<{ sensors: IngestRow[] }>('/api/admin/logs/ingest');
      setIngest(Object.fromEntries(lg.sensors.map((r) => [r.sensorId, r])));
    } catch (e) {
      setErr((e as Error).message);
    }
  }, [farmId]);
  useEffect(() => {
    load();
  }, [load]);

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

  const zoneCode = (z: number | null) => zones.find((x) => x.zoneId === z)?.zoneCode ?? '공용';
  const addSensor = (e: FormEvent) => {
    e.preventDefault();
    act(() => post('/api/admin/sensors', { ...nf, farmId, gatewayId: farmId, zoneId: nf.zoneId || null }), `${nf.sensorCode} 센서를 등록했습니다.`);
  };

  return (
    <div>
      <PageTitle title="센서·장치 관리" desc="센서 ID·설치 위치·상태와 데이터 수집 상황. 수집 주기는 1분(시간당 60건)입니다." />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <Card title={`센서 ${sensors.length}개`}>
        <Table head={['ID', '지표', '구역', '설치 위치', '유효 범위', '상태', '최근 1시간 수신', '마지막 수신', '']}>
          {sensors.map((s) => {
            const r = ingest[s.sensorId];
            return (
              <tr key={s.sensorId}>
                <td className="py-2 pr-3 font-medium">{s.sensorCode}{s.isSimulated && <span className="ml-1 text-[10px] text-slate-400">SIM</span>}</td>
                <td className="pr-3">{METRIC_LABEL[s.metric]}</td>
                <td className="pr-3">{zoneCode(s.zoneId)}</td>
                <td className="max-w-[220px] pr-3 text-xs text-slate-600">{s.installNote}</td>
                <td className="whitespace-nowrap pr-3 text-xs">{s.validMin}~{s.validMax}{unit(s.unit)}</td>
                <td className="pr-3"><Badge tone={s.status === 'ACTIVE' ? 'green' : s.status === 'FAULT' ? 'red' : 'gray'}>{s.status}</Badge></td>
                <td className="pr-3">{r ? `${r.receivedLastHour}/${r.expectedPerHour}` : '-'}</td>
                <td className="whitespace-nowrap pr-3 text-xs">{ago(s.lastReceivedAt)}</td>
                <td className="whitespace-nowrap">
                  <Button small variant="ghost" onClick={() => {
                    const note = window.prompt('설치 위치', s.installNote ?? '');
                    if (note !== null) act(() => patch(`/api/admin/sensors/${s.sensorId}`, { installNote: note }), '설치 위치를 바꿨습니다.');
                  }}>위치</Button>
                  {s.status !== 'RETIRED' && <Button small variant="ghost" onClick={() => act(() => patch(`/api/admin/sensors/${s.sensorId}`, { status: 'RETIRED' }), `${s.sensorCode}를 폐기 처리했습니다(이력 보존).`)}>폐기</Button>}
                </td>
              </tr>
            );
          })}
        </Table>
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title={`제어 장치 ${devices.length}개`} className="xl:col-span-2">
          <Table head={['ID', '이름', '유형', '구역', '상태', '모드', '']}>
            {devices.map((d) => (
              <tr key={d.deviceId}>
                <td className="py-2 pr-3 font-medium">{d.deviceCode}</td>
                <td className="pr-3">{d.deviceName}</td>
                <td className="pr-3">{d.deviceType}</td>
                <td className="pr-3">{zoneCode(d.zoneId)}</td>
                <td className="pr-3">{STATE_LABEL[d.state] ?? d.state}</td>
                <td className="pr-3">{d.mode === 'AUTO' ? '자동' : '수동'}</td>
                <td><Button small variant="ghost" onClick={() => {
                  const n = window.prompt('장치 이름', d.deviceName);
                  if (n) act(() => patch(`/api/admin/devices/${d.deviceId}`, { deviceName: n }), '이름을 바꿨습니다.');
                }}>이름</Button></td>
              </tr>
            ))}
          </Table>
          <p className="mt-2 text-xs text-slate-500">장치별 제어 이력은 '스마트팜 제어' 또는 '시스템·데이터 로그'에서 확인합니다.</p>
        </Card>
        <Card title="센서 등록">
          <form onSubmit={addSensor} className="space-y-3">
            <Field label="센서 ID (예: S-T03)"><input className={inputCls} value={nf.sensorCode} onChange={(e) => setNf({ ...nf, sensorCode: e.target.value })} required /></Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="지표">
                <select className={inputCls} value={nf.metric} onChange={(e) => setNf({ ...nf, metric: e.target.value })}>
                  {Object.entries(METRIC_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </Field>
              <Field label="단위"><input className={inputCls} value={nf.unit} onChange={(e) => setNf({ ...nf, unit: e.target.value })} /></Field>
              <Field label="최소"><input type="number" className={inputCls} value={nf.validMin} onChange={(e) => setNf({ ...nf, validMin: Number(e.target.value) })} /></Field>
              <Field label="최대"><input type="number" className={inputCls} value={nf.validMax} onChange={(e) => setNf({ ...nf, validMax: Number(e.target.value) })} /></Field>
            </div>
            <Field label="구역">
              <select className={inputCls} value={nf.zoneId} onChange={(e) => setNf({ ...nf, zoneId: Number(e.target.value) })}>
                <option value={0}>공용</option>
                {zones.map((z) => <option key={z.zoneId} value={z.zoneId}>{z.zoneCode} {z.zoneName}</option>)}
              </select>
            </Field>
            <Field label="설치 위치"><input className={inputCls} value={nf.installNote} onChange={(e) => setNf({ ...nf, installNote: e.target.value })} /></Field>
            <Button type="submit">등록</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
