import { FormEvent, useCallback, useEffect, useState } from 'react';
import { del, get, patch, post } from '../../api/client';
import type { DeviceView, Gateway, Sensor, Zone } from '../../api/types';
import { METRIC_LABEL, STATE_LABEL, ago, unit } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, ConfirmDialog, ErrorBox, Field, Modal, PageTitle, Table, inputCls } from '../../components/ui';

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
  const [gws, setGws] = useState<Gateway[]>([]);
  const [nz, setNz] = useState({ zoneCode: '', zoneName: '', areaM2: '' });
  const [delZone, setDelZone] = useState<Zone | null>(null);
  const [token, setToken] = useState<{ code: string; token: string } | null>(null);
  const [askToken, setAskToken] = useState<Gateway | null>(null);
  const [nf, setNf] = useState({ sensorCode: '', metric: 'TEMP', unit: 'C', zoneId: 0, validMin: -20, validMax: 60, installNote: '' });

  const load = useCallback(async () => {
    if (!farmId) return;
    try {
      setSensors(await get<Sensor[]>(`/api/sensors?farmId=${farmId}`));
      setDevices(await get<DeviceView[]>(`/api/devices?farmId=${farmId}`));
      setZones(await get<Zone[]>(`/api/farms/${farmId}/zones`));
      setGws((await get<{ gateways: Gateway[] }>(`/api/farms/${farmId}/dashboard`)).gateways);
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

  const counts = (z: number) => `센서 ${sensors.filter((s) => s.zoneId === z).length} · 장치 ${devices.filter((d) => d.zoneId === z).length}`;

  return (
    <div>
      <PageTitle title="센서·장치 관리" desc="센서 ID·설치 위치·상태와 데이터 수집 상황. 수집 주기는 1분(시간당 60건)입니다." />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <div className="mb-4 grid gap-4 xl:grid-cols-3">
        <Card title="관리 구역 (REQ-F-13)" className="xl:col-span-2">
          <Table head={['코드', '이름', '면적(㎡)', '연결', '']}>
            {zones.map((z) => (
              <tr key={z.zoneId}>
                <td className="py-2 pr-3 font-medium">{z.zoneCode}</td>
                <td className="pr-3">{z.zoneName}</td>
                <td className="pr-3">{z.areaM2 ?? '-'}</td>
                <td className="pr-3 text-xs">{counts(z.zoneId)}</td>
                <td><Button small variant="ghost" onClick={() => setDelZone(z)}>삭제</Button></td>
              </tr>
            ))}
          </Table>
          <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={(e) => {
            e.preventDefault();
            act(() => post('/api/admin/zones', { farmId, zoneCode: nz.zoneCode, zoneName: nz.zoneName, areaM2: Number(nz.areaM2) }), `${nz.zoneCode} 구역을 등록했습니다.`)
              .then(() => setNz({ zoneCode: '', zoneName: '', areaM2: '' }));
          }}>
            <div className="w-24"><Field label="코드"><input className={inputCls} value={nz.zoneCode} onChange={(e) => setNz({ ...nz, zoneCode: e.target.value })} placeholder="Z3" required /></Field></div>
            <div className="w-40"><Field label="이름"><input className={inputCls} value={nz.zoneName} onChange={(e) => setNz({ ...nz, zoneName: e.target.value })} required /></Field></div>
            <div className="w-28"><Field label="면적㎡"><input type="number" step="0.01" className={inputCls} value={nz.areaM2} onChange={(e) => setNz({ ...nz, areaM2: e.target.value })} required /></Field></div>
            <Button type="submit">구역 등록</Button>
          </form>
          <p className="mt-2 text-xs text-slate-500">센서·장치가 연결된 구역은 삭제되지 않습니다. 먼저 센서·장치의 구역을 바꾸세요.</p>
        </Card>
        <Card title="현장 게이트웨이">
          <ul className="space-y-2 text-sm">
            {gws.map((g) => (
              <li key={g.gatewayId} className="rounded-lg bg-slate-50 p-2">
                <div className="flex items-center justify-between"><b>{g.gatewayCode}</b><Badge tone={g.status === 'ONLINE' ? 'green' : 'red'}>{g.status}</Badge></div>
                <div className="text-xs text-slate-600">하트비트 {ago(g.lastHeartbeatAt)} · {g.isSimulated ? '시뮬레이터' : '실장비'}</div>
                <div className="mt-1"><Button small variant="secondary" onClick={() => setAskToken(g)}>HTTP 대체 수집 토큰 발급</Button></div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500">MQTT가 끊겼을 때 게이트웨이가 /api/ingest/sensor-data 로 측정값을 올릴 때 쓰는 기기 토큰입니다 (API-26).</p>
        </Card>
      </div>

      <Card title={`센서 ${sensors.length}개`}>
        <Table head={['ID', '지표', '구역', '설치 위치', '유효 범위', '상태', '최근 1시간 수신', '마지막 수신', '']}>
          {sensors.map((s) => {
            const r = ingest[s.sensorId];
            return (
              <tr key={s.sensorId}>
                <td className="py-2 pr-3 font-medium">{s.sensorCode}{s.isSimulated && <span className="ml-1 text-xs text-slate-500">SIM</span>}</td>
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
          <p className="mt-2 text-xs text-slate-500">장치별 제어 이력은 '제어 이력' 또는 '시스템·데이터 로그'에서 확인합니다.</p>
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
      <ConfirmDialog open={!!delZone} title="구역 삭제" danger confirmLabel="삭제" body={delZone && <>{delZone.zoneCode} {delZone.zoneName} 구역을 삭제합니다.</>}
        onConfirm={() => { const z = delZone!; setDelZone(null); act(() => del(`/api/admin/zones/${z.zoneId}`), `${z.zoneCode} 구역을 삭제했습니다.`); }}
        onCancel={() => setDelZone(null)} />
      <ConfirmDialog open={!!askToken} title="기기 토큰 발급" confirmLabel="발급"
        body={askToken && <>{askToken.gatewayCode}의 새 토큰을 발급하면 이전 토큰은 바로 쓸 수 없게 됩니다.</>}
        onConfirm={async () => {
          const g = askToken!;
          setAskToken(null);
          try {
            const r = await post<{ deviceToken: string }>(`/api/admin/gateways/${g.gatewayId}/token`);
            setToken({ code: g.gatewayCode, token: r.deviceToken });
          } catch (e) {
            setErr((e as Error).message);
          }
        }} onCancel={() => setAskToken(null)} />
      <Modal open={!!token} title={`${token?.code} 기기 토큰`} onClose={() => setToken(null)}>
        <p className="text-sm text-slate-600">이 창을 닫으면 다시 볼 수 없습니다. 게이트웨이 설정에 바로 저장하세요. 서버에는 해시만 저장됩니다.</p>
        <div className="mt-3 break-all rounded-lg bg-slate-50 p-3 font-mono text-sm">{token?.token}</div>
        <div className="mt-3 flex justify-end"><Button onClick={() => setToken(null)}>닫기</Button></div>
      </Modal>
    </div>
  );
}
