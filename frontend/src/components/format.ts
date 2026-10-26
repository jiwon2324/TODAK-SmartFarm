// 화면 표기 규칙: 단위·라벨·시각 형식을 한 곳에서 관리

export const METRIC_LABEL: Record<string, string> = {
  TEMP: '온도',
  HUMI: '습도',
  CO2: 'CO₂',
  SOLAR: '일사량',
  SUBSTRATE: '배지 수분',
  EC: 'EC',
  PH: 'pH',
  TEMP_OUT: '외부 온도',
};

export const UNIT_LABEL: Record<string, string> = { C: '℃', '%': '%', ppm: 'ppm', 'W/m2': 'W/㎡', 'dS/m': 'dS/m', pH: '' };

export const STATE_LABEL: Record<string, string> = { ON: '켜짐', OFF: '꺼짐', OPEN: '열림', CLOSE: '닫힘' };

export const STAGE_LABEL: Record<string, string> = { NURSERY: '육묘', GROWTH: '생육', FLOWER: '개화', HARVEST: '수확' };

export const ALERT_TYPE_LABEL: Record<string, string> = {
  THRESHOLD: '기준 이탈',
  SENSOR_FAIL: '센서 무응답',
  OUTLIER: '측정 이상',
  DEVICE_NOACK: '장치 응답 없음',
  GW_OFFLINE: '통신 장애',
  POWER: '정전',
  BEE: '벌통 교체',
  HARVEST: '수확 시기',
};

export const COMMAND_STATUS_LABEL: Record<string, string> = {
  REQUESTED: '요청',
  SENT: '전송됨',
  ACKED: '실행 확인',
  FAILED: '실패',
  TIMEOUT: '응답 없음',
  REJECTED: '거부',
};

export const SOURCE_LABEL: Record<string, string> = { AUTO: '자동', MANUAL: '수동', SAFETY: '안전 한계', FAILSAFE: '현장 안전 운전' };

export function unit(u: string) {
  return UNIT_LABEL[u] ?? u;
}

export function fmtTime(s?: string | null) {
  if (!s) return '-';
  const d = new Date(s);
  return d.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
}

export function fmtHm(s: string) {
  const d = new Date(s);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function fmtMd(s: string) {
  const d = new Date(s);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function ago(s?: string | null) {
  if (!s) return '수신 없음';
  const sec = Math.round((Date.now() - new Date(s).getTime()) / 1000);
  if (sec < 60) return `${Math.max(sec, 0)}초 전`;
  if (sec < 3600) return `${Math.round(sec / 60)}분 전`;
  if (sec < 86400) return `${Math.round(sec / 3600)}시간 전`;
  return `${Math.round(sec / 86400)}일 전`;
}

export function isActiveState(type: string, state: string) {
  if (type === 'VENT') return state === 'OPEN';
  if (type === 'SHADE') return state === 'CLOSE';
  return state === 'ON';
}

export function isoLocal(d: Date) {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:00`;
}

export function isoDate(d: Date) {
  return isoLocal(d).slice(0, 10);
}
