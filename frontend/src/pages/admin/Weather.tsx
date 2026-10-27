import { useEffect, useState } from 'react';
import { ApiError, get, post } from '../../api/client';
import { isoDate } from '../../components/format';
import { Button, Card, ConfirmDialog, Empty, ErrorBox, PageTitle, Table } from '../../components/ui';

interface WeatherRow {
  stationId: string;
  obsDate: string;
  tavgC: number | null;
  tminC: number | null;
  tmaxC: number | null;
  rainMm: number | null;
  rhPct: number | null;
  sunshineHr: number | null;
  missingFlags: string | null;
  sourceFile: string;
}

/** SCR-A6 외부 기상 자료: 기상자료개방포털 ASOS 일자료 CSV 가져오기 [REQ-F-15] */
export default function Weather() {
  const [rows, setRows] = useState<WeatherRow[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [dup, setDup] = useState<string | null>(null);

  const load = () => {
    const to = new Date();
    const from = new Date(to.getTime() - 400 * 86400000);
    get<WeatherRow[]>(`/api/admin/weather?station=202&from=${isoDate(from)}&to=${isoDate(to)}`).then(setRows).catch((e) => setErr(e.message));
  };
  useEffect(load, []);

  // REQ-F-15 예외: 이미 저장된 날짜가 있으면 서버가 409로 확인을 요청하고, 확인하면 overwrite=true로 다시 보낸다
  const upload = async (overwrite = false) => {
    if (!file) {
      setErr('CSV 파일을 고르세요');
      return;
    }
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await post<{ station: string; rows: number; missingDays: number; overwritten: number; skipped: number }>(`/api/admin/weather/import?overwrite=${overwrite}`, fd);
      setMsg(`지점 ${r.station}: ${r.rows}일 저장 (결측 포함 ${r.missingDays}일, 덮어쓰기 ${r.overwritten}일, 건너뜀 ${r.skipped}행)`);
      setErr(null);
      load();
    } catch (e) {
      if (e instanceof ApiError && e.code === 'DUPLICATE_DATES') setDup(e.message);
      else setErr((e as Error).message);
    }
  };

  return (
    <div>
      <PageTitle title="외부 기상 자료" desc="양평 종관기상관측(ASOS 202) 일자료. 외부 GDD와 내부·외부 기온 비교에 쓰입니다." />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <Card title="CSV 가져오기">
        <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-slate-600">
          <li>기상자료개방포털(data.kma.go.kr) → 기후통계분석/데이터 → 종관기상관측(ASOS) → 일자료</li>
          <li>지점: 양평(202), 기간 선택, 요소: 평균·최저·최고기온, 일강수량, 평균 상대습도, 합계 일조시간</li>
          <li>CSV로 내려받아 아래에서 올립니다 (CP949·UTF-8 모두 가능, 같은 날짜는 덮어씀)</li>
        </ol>
        <div className="flex flex-wrap items-center gap-2">
          <input type="file" aria-label="기상청 일자료 CSV 파일" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
          <Button onClick={() => upload(false)}>가져오기</Button>
        </div>
      </Card>
      <Card title={`저장된 일자료 ${rows.length}일`} className="mt-4">
        {rows.length === 0 ? <Empty>아직 가져온 기상청 자료가 없습니다. 시뮬레이션 값으로 대신 채우지 않습니다.</Empty> : (
          <Table head={['날짜', '평균', '최저', '최고', '강수', '습도', '일조', '결측', '파일']}>
            {[...rows].reverse().map((r) => (
              <tr key={r.obsDate}>
                <td className="py-1.5 pr-3">{r.obsDate}</td><td className="pr-3">{r.tavgC ?? '-'}</td><td className="pr-3">{r.tminC ?? '-'}</td><td className="pr-3">{r.tmaxC ?? '-'}</td>
                <td className="pr-3">{r.rainMm ?? '-'}</td><td className="pr-3">{r.rhPct ?? '-'}</td><td className="pr-3">{r.sunshineHr ?? '-'}</td>
                <td className="pr-3 text-xs text-red-600">{r.missingFlags}</td><td className="pr-3 text-xs text-slate-500">{r.sourceFile}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
      <ConfirmDialog open={!!dup} title="같은 날짜 덮어쓰기" body={dup} confirmLabel="덮어쓰기"
        onConfirm={() => { setDup(null); upload(true); }} onCancel={() => setDup(null)} />
    </div>
  );
}
