export type Role = 'ADMIN' | 'FARMER' | 'VIEWER';

export interface Me {
  userId: number;
  loginId: string;
  name: string;
  role: Role;
  farmIds: number[];
  phone?: string | null;
  email?: string | null;
  notifyAgreed?: boolean;
  mustChangePassword?: boolean;
  lastLoginAt?: string | null;
  pwChangedAt?: string | null;
  createdAt?: string;
}

export interface Farm {
  farmId: number;
  farmName: string;
  region: string;
  areaM2: number;
  facilityType: string;
  cultureType: string | null;
  kmaStationId: string | null;
}

export interface Zone {
  zoneId: number;
  zoneCode: string;
  zoneName: string;
  areaM2?: number;
}

export interface Reading {
  sensorId: number;
  sensorCode: string;
  metric: string;
  unit: string;
  zoneId: number | null;
  status: string;
  simulated: boolean;
  value?: number;
  measuredAt?: string;
  quality?: string;
  lastReceivedAt?: string | null;
}

export interface DeviceView {
  deviceId: number;
  deviceCode: string;
  deviceType: string;
  deviceName: string;
  zoneId: number | null;
  mode: 'AUTO' | 'MANUAL';
  manualUntil: string | null;
  state: string;
  stateChangedAt: string | null;
  simulated: boolean;
}

export interface Gateway {
  gatewayId: number;
  gatewayCode: string;
  status: string;
  lastHeartbeatAt: string | null;
  isSimulated: boolean;
  syncedStdVersion: number | null;
}

export interface CropCycle {
  cycleId: number;
  farmId: number;
  variety: string | null;
  transplantDate: string;
  currentStage: string;
  gddBaseC: number;
  gddUpperC: number;
}

export interface Dashboard {
  farm: Farm;
  zones: Zone[];
  readings: Reading[];
  devices: DeviceView[];
  gateways: Gateway[];
  openAlerts: number;
  cropCycle: CropCycle | null;
  serverTime: string;
  dliToday: number | null;
  cumGddInternal: number | null;
  lastReceivedAt: string | null;
}

export interface Command {
  commandId: number;
  deviceId: number;
  deviceCode: string;
  deviceName: string;
  action: string;
  source: string;
  status: string;
  retryCount: number;
  reason: string | null;
  requestedAt: string;
  sentAt: string | null;
  ackedAt: string | null;
}

export interface StateLog {
  logId: number;
  deviceCode: string;
  deviceName: string;
  commandId: number | null;
  prevState: string | null;
  newState: string;
  changedBy: string;
  changedAt: string;
}

export interface Alert {
  alertId: number;
  farmId: number;
  type: string;
  severity: 'INFO' | 'WARN' | 'CRITICAL';
  message: string;
  status: 'OPEN' | 'ACK' | 'RESOLVED';
  occurCount: number;
  firstAt: string;
  lastAt: string;
  resolvedAt: string | null;
}

export interface SeriesPoint {
  t: string;
  value?: number;
  avg?: number;
  min?: number;
  max?: number;
  quality?: string;
}

export interface Series {
  sensorId: number;
  sensorCode: string;
  metric: string;
  unit: string;
  simulated: boolean;
  points: SeriesPoint[];
}

export interface GddDay {
  date: string;
  tavg: number | null;
  gdd: number | null;
  cumGdd: number | null;
  coverage: number;
  complete: boolean;
}

export interface GddResult {
  cycleId: number;
  transplantDate: string;
  source: string;
  method: string;
  base: number;
  upper: number;
  dataOrigin: string;
  days: GddDay[];
  summary: { elapsedDays: number; missingDays: number; incompleteDays: number; hot35Days: number; cold5Days: number };
}

export interface DailyStat {
  date: string;
  tempAvg?: number;
  tempMin?: number;
  tempMax?: number;
  diurnal?: number;
  humiAvg?: number;
  dliEstimate?: number;
  outSensorAvg?: number;
  kmaTavg?: number;
  kmaTmin?: number;
  kmaTmax?: number;
  dayAvg?: number;
  nightAvg?: number;
  dif?: number;
}

export interface CropStd {
  stdId: number;
  stage: string;
  versionNo: number;
  dayTempMin: number;
  dayTempMax: number;
  nightTempMin: number;
  nightTempMax: number;
  humidityMin: number;
  humidityMax: number;
  ecMin: number;
  ecMax: number;
  phMin: number;
  phMax: number;
  substrateMoistureMin: number | null;
  sourceNote: string | null;
  isCurrent: boolean;
  effectiveFrom: string;
}

export interface ControlRule {
  ruleId: number;
  ruleCode: string;
  ruleName: string;
  metric: string;
  period: string;
  compareOp: string;
  onThreshold: number;
  offThreshold: number;
  targetDeviceType: string;
  minRunSec: number;
  maxRunSec: number | null;
  maxDailyCount: number | null;
  isSafety: boolean;
  priority: number;
  isEnabled: boolean;
  sustainSec: number | null;
  maxPerHour: number | null;
  minIntervalSec: number | null;
  stage2DeviceType: string | null;
  stage2Threshold: number | null;
  stage2DelaySec: number | null;
  alsoCloseType: string | null;
}

export interface AdminUser {
  userId: number;
  loginId: string;
  name: string;
  phone: string | null;
  role: Role;
  email: string | null;
  isActive: boolean;
  approvalStatus: 'PENDING' | 'APPROVED' | 'REJECTED';
  requestedRole: Role | null;
  signupNote: string | null;
  mustChangePassword: boolean;
  pwResetRequestedAt: string | null;
  lastLoginAt: string | null;
  lockedUntil: string | null;
  createdAt: string;
  farmIds: number[];
}

export interface Sensor {
  sensorId: number;
  farmId: number;
  zoneId: number | null;
  gatewayId: number;
  sensorCode: string;
  metric: string;
  unit: string;
  validMin: number;
  validMax: number;
  spikeLimit: number | null;
  installNote: string | null;
  isSimulated: boolean;
  status: string;
  lastReceivedAt: string | null;
}
