import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { get } from '../api/client';
import type { Farm } from '../api/types';
import { useAuth } from '../hooks/auth';

const FarmCtx = createContext<{ farmId: number | null; farms: Farm[]; setFarmId: (id: number) => void }>({ farmId: null, farms: [], setFarmId: () => {} });
export const useFarm = () => useContext(FarmCtx);

const FARMER_NAV = [
  { to: '/farm', label: '대시보드', icon: '◎', end: true },
  { to: '/farm/analytics', label: '환경 분석', icon: '∿' },
  { to: '/farm/control', label: '스마트팜 제어', icon: '⏻' },
  { to: '/farm/crop', label: '재배 관리', icon: '❀' },
  { to: '/farm/alerts', label: '알림 센터', icon: '!' },
];

const ADMIN_NAV = [
  { to: '/admin', label: '관리자 대시보드', icon: '▦', end: true },
  { to: '/admin/users', label: '사용자 관리', icon: '☺' },
  { to: '/admin/equipment', label: '센서·장치 관리', icon: '⚙' },
  { to: '/admin/standards', label: '기준값·제어 규칙', icon: '≡' },
  { to: '/admin/logs', label: '시스템·데이터 로그', icon: '☰' },
  { to: '/admin/weather', label: '외부 기상 자료', icon: '☂' },
];

export function Layout({ children }: { children: ReactNode }) {
  const { me, logout } = useAuth();
  const nav = useNavigate();
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

  const items = me?.role === 'ADMIN' ? [...ADMIN_NAV, ...FARMER_NAV] : FARMER_NAV;
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-leaf-50 font-semibold text-leaf-700' : 'text-slate-600 hover:bg-slate-100'}`;

  return (
    <FarmCtx.Provider value={{ farmId, farms, setFarmId: choose }}>
      <div className="min-h-screen md:flex">
        <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-4 md:block">
          <div className="mb-6">
            <div className="text-lg font-extrabold text-leaf-700">TODAK</div>
            <div className="text-xs text-slate-500">방울토마토 스마트 농업 정보시스템</div>
          </div>
          {me?.role === 'ADMIN' && <div className="mb-1 px-3 text-xs font-semibold text-slate-400">관리자</div>}
          <nav className="space-y-1">
            {items.map((i, idx) => (
              <div key={i.to}>
                {me?.role === 'ADMIN' && idx === ADMIN_NAV.length && <div className="mb-1 mt-4 px-3 text-xs font-semibold text-slate-400">농가 화면</div>}
                <NavLink to={i.to} end={i.end} className={linkCls}>
                  <span className="w-4 text-center">{i.icon}</span>
                  {i.label}
                </NavLink>
              </div>
            ))}
          </nav>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/95 px-4 py-2 backdrop-blur">
            <span className="font-extrabold text-leaf-700 md:hidden">TODAK</span>
            <select aria-label="농장 선택" value={farmId ?? ''} onChange={(e) => choose(Number(e.target.value))}
              className="max-w-[55vw] rounded-lg border border-slate-300 px-2 py-1 text-sm">
              {farms.map((f) => (
                <option key={f.farmId} value={f.farmId}>{f.farmName}</option>
              ))}
            </select>
            <div className="ml-auto flex items-center gap-2 text-sm">
              <span className="hidden text-slate-600 sm:inline">{me?.name}</span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{me?.role === 'ADMIN' ? '관리자' : '농가'}</span>
              <button className="text-slate-500 hover:text-slate-800" onClick={async () => { await logout(); nav('/login'); }}>로그아웃</button>
            </div>
          </header>
          <main className="flex-1 p-4 pb-24 md:p-6 md:pb-6">{farmId ? children : <div className="text-slate-500">접근 가능한 농장이 없습니다. 관리자에게 권한을 요청하세요.</div>}</main>
        </div>
        <nav className="fixed inset-x-0 bottom-0 z-30 flex overflow-x-auto border-t border-slate-200 bg-white md:hidden">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end}
              className={({ isActive }) => `flex min-w-[72px] flex-1 flex-col items-center px-1 py-2 text-[11px] ${isActive ? 'text-leaf-700' : 'text-slate-500'}`}>
              <span className="text-base leading-none">{i.icon}</span>
              <span className="mt-1 whitespace-nowrap">{i.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </FarmCtx.Provider>
  );
}
