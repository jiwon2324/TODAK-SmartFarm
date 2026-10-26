import { describe, expect, it } from 'vitest';
import { STATE_LABEL, isActiveState, unit } from '../components/format';

describe('format', () => {
  it('장치 유형별 작동 상태를 판정한다', () => {
    expect(isActiveState('VENT', 'OPEN')).toBe(true);
    expect(isActiveState('VENT', 'CLOSE')).toBe(false);
    expect(isActiveState('SHADE', 'CLOSE')).toBe(true);
    expect(isActiveState('FAN', 'ON')).toBe(true);
    expect(isActiveState('FAN', 'OFF')).toBe(false);
  });
  it('단위와 상태를 한글로 표시한다', () => {
    expect(unit('C')).toBe('℃');
    expect(STATE_LABEL.OPEN).toBe('열림');
  });
});
