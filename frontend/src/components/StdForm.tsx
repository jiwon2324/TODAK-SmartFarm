import { useEffect, useState } from 'react';
import { post } from '../api/client';
import type { CropStd } from '../api/types';
import { STAGE_LABEL } from './format';
import { Button, Field, inputCls } from './ui';

export const STD_FIELDS: [keyof CropStd, string][] = [
  ['dayTempMin', '주간 최저℃'], ['dayTempMax', '주간 최고℃'], ['nightTempMin', '야간 최저℃'], ['nightTempMax', '야간 최고℃'],
  ['humidityMin', '습도 최저%'], ['humidityMax', '습도 최고%'], ['ecMin', 'EC 최저'], ['ecMax', 'EC 최고'],
  ['phMin', 'pH 최저'], ['phMax', 'pH 최고'], ['substrateMoistureMin', '배지수분 하한%'],
];

/** 생육 단계별 재배 기준값 새 버전 등록 (UC-05, API-16) — 관리자·농가 공용. 범위 역전은 화면과 서버 모두 거부 */
export function StdForm({ farmId, current, initialStage = 'GROWTH', disabled, onSaved, onError }: {
  farmId: number; current: CropStd[]; initialStage?: string; disabled?: boolean; onSaved: (msg: string) => void; onError: (msg: string) => void;
}) {
  const [stage, setStage] = useState(initialStage);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [note, setNote] = useState('');

  useEffect(() => {
    const cur = current.find((x) => x.stage === stage);
    if (cur) {
      setDraft(Object.fromEntries(STD_FIELDS.map(([k]) => [k, String(cur[k] ?? '')])));
      setNote(cur.sourceNote ?? '');
    }
  }, [current, stage]);

  const pairs: [string, string, string][] = [['dayTempMin', 'dayTempMax', '주간 온도'], ['nightTempMin', 'nightTempMax', '야간 온도'],
    ['humidityMin', 'humidityMax', '습도'], ['ecMin', 'ecMax', 'EC'], ['phMin', 'phMax', 'pH']];
  const inverted = pairs.filter(([a, b]) => draft[a] !== '' && draft[b] !== '' && Number(draft[a]) >= Number(draft[b])).map((p) => p[2]);

  const save = async () => {
    if (inverted.length) {
      onError(`${inverted.join(', ')}: 최솟값이 최댓값보다 작아야 합니다.`);
      return;
    }
    try {
      await post('/api/crop-standards', {
        farmId, stage, sourceNote: note,
        ...Object.fromEntries(STD_FIELDS.map(([k]) => [k, draft[k as string] === '' ? null : Number(draft[k as string])])),
      });
      onSaved(`${STAGE_LABEL[stage]} 기준을 새 버전으로 저장하고 현장 게이트웨이에 다시 보냈습니다.`);
    } catch (e) {
      onError((e as Error).message);
    }
  };

  return (
    <fieldset disabled={disabled} className="disabled:opacity-60">
      <Field label="생육 단계">
        <select className={inputCls} value={stage} onChange={(e) => setStage(e.target.value)}>
          {Object.entries(STAGE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </Field>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {STD_FIELDS.map(([k, l]) => (
          <Field key={k} label={l}><input type="number" step="0.1" inputMode="decimal" className={inputCls} value={draft[k as string] ?? ''}
            onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} /></Field>
        ))}
      </div>
      {inverted.length > 0 && <p className="mt-2 text-xs text-red-700">{inverted.join(', ')}: 최솟값이 최댓값보다 작아야 합니다.</p>}
      <div className="mt-2"><Field label="근거 출처"><input className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} /></Field></div>
      <div className="mt-3"><Button onClick={save} disabled={disabled}>새 버전 저장</Button></div>
    </fieldset>
  );
}
