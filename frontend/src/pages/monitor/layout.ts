// 하우스 평면 배치 (제출 PPT의 '센서 배치도'·'제어장치·통신 배치도', docs/Diagrams/l_sensors.png·l_devices.png)
// 같은 함체·인접 센서(T/H, EC/pH)는 값 표시가 겹치지 않게 조금 벌려 놓았다.
// 좌표는 하우스 안쪽 기준 백분율(x: 출입구 0 → 안쪽 100, y: 위 0 → 아래 100). 그림에서 잰 값이다.
// 41.5m × 8m, 베드 4열(코이어 배지 35.5m), Z1 입구측 / Z2 안쪽 (각 약 166㎡)

export interface Spot { x: number; y: number }

export const SENSOR_SPOTS: Record<string, Spot> = {
  'S-TO01': { x: -4, y: 12 },      // 하우스 밖 북측
  'S-SOL01': { x: 50, y: 24 },
  'S-T01': { x: 21.5, y: 50 },
  'S-H01': { x: 28.5, y: 50 },     // S-T01과 같은 함체 → 옆에 나란히
  'S-CO2-01': { x: 50, y: 50 },
  'S-T02': { x: 71.5, y: 50 },
  'S-H02': { x: 78.5, y: 50 },
  'S-SM01': { x: 29, y: 69 },
  'S-SM02': { x: 72, y: 69 },
  'S-EC01': { x: 3.5, y: 80 },
  'S-PH01': { x: 10.5, y: 80 },
};

export const DEVICE_SPOTS: Record<string, Spot> = {
  'D-VENT02': { x: 41, y: 2 },
  'D-VENT01': { x: 41, y: 98 },
  'D-HEAT01': { x: 3.6, y: 18 },
  'D-VALVE01': { x: 8, y: 35 },
  'D-VALVE02': { x: 8, y: 65 },
  'D-NUT01': { x: 15, y: 94 },
  'D-LIGHT01': { x: 25, y: 25 },
  'D-SHADE01': { x: 59, y: 15 },
  'D-LIGHT02': { x: 75, y: 25 },
  'D-FAN02': { x: 99.3, y: 31 },
  'D-FAN01': { x: 99.3, y: 69 },
};

/** 제어반 CP-01 (게이트웨이·라우터·UPS) */
export const PANEL_SPOT: Spot = { x: 2, y: 50 };

/** 베드 4열의 세로 위치 (%) */
export const BED_ROWS = [13, 37, 61, 85];
export const BED_X = [8.4, 94];
/** Z1/Z2 경계 (%) */
export const ZONE_SPLIT = 50;

// SVG 좌표: viewBox 0 0 1000 330, 하우스 안쪽 사각형
export const HOUSE = { x: 80, y: 30, w: 880, h: 270 };
export const toSvg = (p: Spot) => ({ x: HOUSE.x + (HOUSE.w * p.x) / 100, y: HOUSE.y + (HOUSE.h * p.y) / 100 });
