import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { get } from '../api/client';
import type { Farm } from '../api/types';
import { useAuth } from '../hooks/auth';
import { Bell, CloudSun, Cpu, Gauge, History, LayoutDashboard, LineChart, ListChecks, Menu, Power, ScanSearch, ScrollText,
  SlidersHorizontal, Sprout, UserRound, Users, X } from 'lucide-react';
import { ROLE_LABEL } from './password';
import { Notice } from './ui';
import { SNAPSHOT, snapshotAt } from '../snapshot';

const FarmCtx = createContext<{ farmId: number | null; farms: Farm[]; setFarmId: (id: number) => void }>({ farmId: null, farms: [], setFarmId: () => {} });
export const useFarm = () => useContext(FarmCtx);

// 메뉴 아이콘: Lucide 단색 선 아이콘(ISC) — 로고와 같은 선 스타일로 통일
// 개발 계획서 16장 화면 구조도: 로그인 → 대시보드 + 메뉴 7개 (SCR-02~09), 관리자 전용 설정 (SCR-10 · 후속 지시서 관리자 화면)
const FARMER_NAV = [
  { to: '/farm', label: '대시보드', short: '대시보드', icon: LayoutDashboard, end: true, scr: 'SCR-02' },
  { to: '/farm/graph', label: '환경 그래프', short: '그래프', icon: LineChart, scr: 'SCR-03' },
  { to: '/farm/control', label: '장치 제어', short: '제어', icon: Power, scr: 'SCR-04' },
  { to: '/farm/history', label: '제어 이력', short: '이력', icon: History, scr: 'SCR-05' },
  { to: '/farm/alerts', label: '알림', short: '알림', icon: Bell, scr: 'SCR-06' },
  { to: '/farm/standards', label: '재배 기준값·제어 규칙', short: '기준값', icon: SlidersHorizontal, scr: 'SCR-07' },
  { to: '/farm/growth', label: '생육 분석 (GDD·기상)', short: '생육', icon: Sprout, scr: 'SCR-08' },
  { to: '/farm/harvest', label: '수확 판별', short: '수확', icon: ScanSearch, scr: 'SCR-09' },
];

const ADMIN_NAV = [
  { to: '/admin', label: '관리자 대시보드', short: '관리', icon: Gauge, end: true, scr: 'SCR-A1' },
  { to: '/admin/users', label: '사용자 관리', short: '사용자', icon: Users, scr: 'SCR-10' },
  { to: '/admin/equipment', label: '구역·센서·장치', short: '장비', icon: Cpu, scr: 'SCR-10' },
  { to: '/admin/standards', label: '기준값·규칙 관리', short: '규칙', icon: ListChecks, scr: 'SCR-A4' },
  { to: '/admin/logs', label: '시스템·데이터 로그', short: '로그', icon: ScrollText, scr: 'SCR-A5' },
  { to: '/admin/weather', label: '외부 기상 자료', short: '기상', icon: CloudSun, scr: 'SCR-A6' },
];

// 모바일 하단 탭 5개 (계획서 화면 구조도 주석: 대시보드·그래프·제어·알림·더보기)
const MOBILE_TABS = ['/farm', '/farm/graph', '/farm/control', '/farm/alerts'];

export function Layout({ children }: { children: ReactNode }) {
  const { me, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const denied = (loc.state as { denied?: boolean } | null)?.denied;
  const [farms, setFarms] = useState<Farm[]>([]);
  const [farmId, setFarmId] = useState<number | null>(() => {
    try {
      return Number(localStorage.getItem('todak.farm')) || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    get<Farm[]>('/api/farms').then((f) => {
      setFarms(f);
      if (!f.some((x) => x.farmId === farmId) && f.length) setFarmId(f[0].farmId);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const choose = (id: number) => {
    setFarmId(id);
    try {
      localStorage.setItem('todak.farm', String(id));
    } catch {
      /* 저장 실패 무시 */
    }
  };

  const [more, setMore] = useState(false);
  const isAdmin = me?.role === 'ADMIN';
  const tabs = FARMER_NAV.filter((i) => MOBILE_TABS.includes(i.to));
  const moreItems = [...FARMER_NAV.filter((i) => !MOBILE_TABS.includes(i.to)), ...(isAdmin ? ADMIN_NAV : []), { to: '/account', label: '내 정보', short: '내 정보', icon: UserRound, scr: '' }];
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-leaf-50 font-semibold text-leaf-700' : 'text-slate-600 hover:bg-slate-100'}`;

  return (
    <FarmCtx.Provider value={{ farmId, farms, setFarmId: choose }}>
      <div className="min-h-screen md:flex">
        <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-4 md:block">
          <div className="mb-6">
            <div className="flex items-center gap-2.5"><img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" className="h-9 w-9 rounded-[10px] shadow-sm" /><img src={`${import.meta.env.BASE_URL}todak-wordmark.svg`} alt="TODAK" className="h-[18px]" /></div>
            <div className="text-xs text-slate-500">방울토마토 스마트 농업 정보시스템</div>
          </div>
          <nav aria-label="주 메뉴">
            <div className="mb-1 px-3 text-xs font-semibold text-slate-500">농장</div>
            <div className="space-y-0.5">
              {FARMER_NAV.map((i) => (
                <NavLink key={i.to} to={i.to} end={i.end} className={linkCls} title={i.scr}>
                  <i.icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.9} aria-hidden="true" />{i.label}
                </NavLink>
              ))}
            </div>
            {isAdmin && (
              <>
                <div className="mb-1 mt-5 px-3 text-xs font-semibold text-slate-500">설정 (관리자)</div>
                <div className="space-y-0.5">
                  {ADMIN_NAV.map((i) => (
                    <NavLink key={i.to} to={i.to} end={i.end} className={linkCls} title={i.scr}>
                      <i.icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.9} aria-hidden="true" />{i.label}
                    </NavLink>
                  ))}
                </div>
              </>
            )}
          </nav>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/95 px-4 py-2 backdrop-blur">
            <span className="flex shrink-0 items-center gap-1.5 md:hidden"><img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="TODAK" className="h-8 w-8 rounded-lg" /><img src={`${import.meta.env.BASE_URL}todak-wordmark.svg`} alt="" className="hidden h-3.5 sm:block" /></span>
            <select aria-label="농장 선택" value={farmId ?? ''} onChange={(e) => choose(Number(e.target.value))}
              className="min-w-0 max-w-[45vw] rounded-lg border border-slate-300 px-2 py-1 text-sm">
              {farms.map((f) => (
                <option key={f.farmId} value={f.farmId}>{f.farmName}</option>
              ))}
            </select>
            <div className="ml-auto flex shrink-0 items-center gap-2 text-sm">
              <Link to="/account" className="hidden rounded px-1 text-slate-700 hover:underline sm:inline" title="내 정보">{me?.name}</Link>
              <span className={`hidden whitespace-nowrap rounded px-1.5 py-0.5 text-xs sm:inline ${me?.role === 'VIEWER' ? 'bg-sky-50 text-sky-800' : 'bg-slate-100 text-slate-700'}`}>{ROLE_LABEL[me?.role ?? 'FARMER']}</span>
              <Link to="/account" className="whitespace-nowrap text-slate-600 hover:text-slate-900 sm:hidden" aria-label="내 정보">내 정보</Link>
              <button className="whitespace-nowrap text-slate-600 hover:text-slate-900" onClick={async () => { await logout(); nav('/login', { state: { flash: '로그아웃했습니다.' } }); }}>로그아웃</button>
            </div>
          </header>
          <main className="min-w-0 flex-1 p-4 pb-24 md:p-6 md:pb-6">
            {SNAPSHOT && (
              <Notice tone="info">
                스냅샷 데모: {snapshotAt.slice(0, 10)} {snapshotAt.slice(11, 16)}에 실제 TODAK 시스템에서 기록한 데이터로 화면을 보여 줍니다. 장치 제어·설정 변경은 실행되지 않으며,
                실시간 동작은 <a className="font-medium underline" href="https://jiwon2324.github.io/TODAK-SmartFarm/Demo/">시연 영상</a>에서 볼 수 있습니다.
              </Notice>
            )}
            {denied && <Notice tone="warn">관리자 전용 화면이라 이동할 수 없습니다.</Notice>}
            {me?.role === 'VIEWER' && <Notice tone="info">조회 전용 계정입니다. 장치 제어와 설정 변경은 할 수 없습니다.</Notice>}
            {farmId || loc.pathname === '/account' ? children : <div className="text-slate-600">접근 가능한 농장이 없습니다. 관리자에게 농장 연결을 요청하세요.</div>}
          </main>
        </div>
        <nav aria-label="하단 메뉴" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-slate-200 bg-white md:hidden">
          {tabs.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} aria-label={i.label}
              className={({ isActive }) => `flex flex-col items-center px-1 py-2 text-xs ${isActive ? 'text-leaf-700' : 'text-slate-600'}`}>
              <i.icon className="h-[22px] w-[22px]" strokeWidth={1.9} aria-hidden="true" />
              <span className="mt-1 whitespace-nowrap">{i.short}</span>
            </NavLink>
          ))}
          <button onClick={() => setMore(true)} aria-haspopup="dialog" className={`flex flex-col items-center px-1 py-2 text-xs ${moreItems.some((i) => loc.pathname === i.to) ? 'text-leaf-700' : 'text-slate-600'}`}>
            <Menu className="h-[22px] w-[22px]" strokeWidth={1.9} aria-hidden="true" />
            <span className="mt-1">더보기</span>
          </button>
        </nav>
        {more && (
          <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={() => setMore(false)} role="dialog" aria-modal="true" aria-label="더보기 메뉴">
            <div className="absolute inset-x-0 bottom-0 rounded-t-2xl bg-white p-4 pb-8" onClick={(e) => e.stopPropagation()}>
              <div className="mb-3 flex items-center justify-between">
                <b>전체 메뉴</b>
                <button onClick={() => setMore(false)} aria-label="닫기" className="rounded p-1 text-slate-600"><X className="h-5 w-5" aria-hidden="true" /></button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {moreItems.map((i) => (
                  <NavLink key={i.to} to={i.to} end={'end' in i ? (i as { end?: boolean }).end : false} onClick={() => setMore(false)}
                    className={({ isActive }) => `flex flex-col items-center rounded-lg border p-3 text-center text-xs ${isActive ? 'border-leaf-500 bg-leaf-50 text-leaf-700' : 'border-slate-200 text-slate-700'}`}>
                    <i.icon className="h-6 w-6" strokeWidth={1.8} aria-hidden="true" />
                    <span className="mt-1">{i.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </FarmCtx.Provider>
  );
}
