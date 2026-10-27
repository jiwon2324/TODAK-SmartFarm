import { ReactNode } from 'react';
import { Link } from 'react-router-dom';

const FEATURES = [
  { t: '실시간 하우스 환경', d: '온도·습도·CO₂·일사·배지 수분·EC·pH를 1분마다 확인' },
  { t: '자동 제어와 안전 한계', d: '측창·환기팬·난방·차광·관수를 기준값에 맞춰 자동 운전' },
  { t: '생육 분석', d: '유효적산온도(GDD)와 양평 기상 자료를 나란히 비교' },
];

/** 로그인·회원가입·비밀번호 찾기 공통 화면 틀 (SCR-01) */
export function AuthShell({ children, wide }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <aside className="hidden bg-gradient-to-br from-leaf-700 to-leaf-900 p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div>
          <Link to="/login" className="inline-flex items-center gap-3 text-3xl font-extrabold tracking-tight"><img src="/favicon.svg" alt="" className="h-11 w-11" />TODAK</Link>
          <p className="mt-1 text-sm text-leaf-100">토닥 · 방울토마토 스마트 농업 정보시스템</p>
          <h1 className="mt-12 text-3xl font-bold leading-snug">양평 하우스를<br />어디서나 살피고 돌봅니다</h1>
          <ul className="mt-8 space-y-5">
            {FEATURES.map((f) => (
              <li key={f.t} className="flex gap-3">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-leaf-100" aria-hidden="true" />
                <div>
                  <div className="font-semibold">{f.t}</div>
                  <div className="text-sm text-leaf-100">{f.d}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-leaf-100">현재 표시되는 센서 값은 가상 센서 시뮬레이터(B안)가 만든 시뮬레이션 데이터입니다.</p>
      </aside>
      <main className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
        <div className="mb-6 text-center lg:hidden">
          <Link to="/login" className="inline-flex items-center gap-2 text-3xl font-extrabold text-leaf-700"><img src="/favicon.svg" alt="" className="h-10 w-10" />TODAK</Link>
          <p className="mt-1 text-sm text-slate-600">방울토마토 스마트 농업 정보시스템</p>
        </div>
        <div className={`w-full ${wide ? 'max-w-xl' : 'max-w-md'}`}>{children}</div>
        <footer className="mt-8 flex gap-3 text-xs text-slate-500">
          <Link to="/terms" className="inline-block py-1 hover:underline">이용약관</Link>
          <span aria-hidden="true">·</span>
          <Link to="/privacy" className="inline-block py-1 font-semibold hover:underline">개인정보처리방침</Link>
          <span aria-hidden="true">·</span>
          <span>TODAK v1.1</span>
        </footer>
      </main>
    </div>
  );
}
