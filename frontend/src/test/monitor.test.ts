import { describe, expect, it } from 'vitest';
import { LEVEL, fmtValue } from '../pages/monitor/Monitor';
import { DEVICE_SPOTS, SENSOR_SPOTS, toSvg } from '../pages/monitor/layout';

describe('통합 관제', () => {
  it('값 표기: CO₂·일사는 정수, 나머지는 소수 1자리, 값 없음은 -', () => {
    expect(fmtValue(812.4, 'CO2')).toBe('812');
    expect(fmtValue(23.456, 'TEMP')).toBe('23.5');
    expect(fmtValue(null, 'TEMP')).toBe('-');
  });

  it('판정 5단계마다 화면 글자가 있다 (색만으로 구분하지 않음)', () => {
    expect(Object.values(LEVEL).map((l) => l.label)).toEqual(['정상', '주의', '경보', '끊김', '값 없음']);
  });

  it('PPT 배치도의 센서 11개·장치 11개 위치가 모두 정의되어 있고 평면 안(외부 온도 제외)에 있다', () => {
    expect(Object.keys(SENSOR_SPOTS)).toHaveLength(11);
    expect(Object.keys(DEVICE_SPOTS)).toHaveLength(11);
    for (const [code, s] of Object.entries({ ...SENSOR_SPOTS, ...DEVICE_SPOTS })) {
      if (code === 'S-TO01') continue;
      expect(s.x).toBeGreaterThanOrEqual(0);
      expect(s.x).toBeLessThanOrEqual(100);
      const p = toSvg(s);
      expect(p.x).toBeLessThanOrEqual(1000);
    }
  });
});
