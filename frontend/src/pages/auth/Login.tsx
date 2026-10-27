import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ApiError, get } from '../../api/client';
import { Button, FormField, Notice, PasswordInput, Spinner, inputCls } from '../../components/ui';
import { homeOf, useAuth } from '../../hooks/auth';
import { AuthShell } from './AuthShell';

const SAVED_ID = 'todak.savedId';

/** SCR-01 로그인 [REQ-F-12] — 아이디 저장, 비밀번호 보기, Caps Lock 경고, 상태별 안내(승인 대기·잠금·만료) */
export default function Login() {
  const { me, login, demo, expired } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [loginId, setLoginId] = useState(() => {
    try {
      return localStorage.getItem(SAVED_ID) ?? '';
    } catch {
      return '';
    }
  });
  const [remember, setRemember] = useState(() => !!loginId);
  const [password, setPassword] = useState('');
  const [error, setError] = useState<{ tone: 'error' | 'warn' | 'info'; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoOn, setDemoOn] = useState(false);
  useEffect(() => {
    get<{ enabled: boolean }>('/api/auth/demo').then((r) => setDemoOn(r.enabled)).catch(() => setDemoOn(false));
  }, []);
  const tryDemo = async () => {
    setBusy(true);
    setError(null);
    try {
      nav(homeOf(await demo()), { replace: true });
    } catch (err) {
      setError({ tone: 'error', msg: (err as Error).message });
    } finally {
      setBusy(false);
    }
  };
  const pwRef = useRef<HTMLDivElement>(null);
  const flash = (loc.state as { flash?: string } | null)?.flash;

  useEffect(() => {
    document.title = '로그인 · TODAK';
  }, []);

  if (me) return <Navigate to={homeOf(me)} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!loginId.trim() || !password) {
      setError({ tone: 'error', msg: !loginId.trim() ? '아이디를 입력하세요.' : '비밀번호를 입력하세요.' });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const m = await login(loginId.trim(), password);
      try {
        if (remember) localStorage.setItem(SAVED_ID, loginId.trim());
        else localStorage.removeItem(SAVED_ID);
      } catch {
        /* 저장 실패는 무시 */
      }
      nav(homeOf(m), { replace: true });
    } catch (err) {
      const code = err instanceof ApiError ? err.code : '';
      setPassword('');
      setError({ tone: code === 'ACCOUNT_PENDING' ? 'info' : code === 'ACCOUNT_LOCKED' ? 'warn' : 'error', msg: (err as Error).message });
      pwRef.current?.querySelector('input')?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form onSubmit={submit} noValidate className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-2xl font-bold text-slate-900">로그인</h2>
        <p className="mt-1 text-sm text-slate-600">등록된 계정으로 농장 상태를 확인하세요.</p>
        <div className="mt-5">
          {flash && <Notice tone="ok">{flash}</Notice>}
          {expired && !error && <Notice tone="warn">로그인 유지 시간이 끝났습니다. 다시 로그인하세요.</Notice>}
          {error && <Notice tone={error.tone}>{error.msg}</Notice>}
        </div>
        <div className="space-y-4">
          <FormField id="login-id" label="아이디">
            <input id="login-id" className={inputCls} value={loginId} onChange={(e) => setLoginId(e.target.value)}
              autoComplete="username" autoCapitalize="none" spellCheck={false} autoFocus={!loginId} />
          </FormField>
          <div ref={pwRef}>
            <FormField id="login-pw" label="비밀번호">
              <PasswordInput id="login-pw" value={password} onChange={setPassword} autoComplete="current-password" />
            </FormField>
          </div>
          <div className="flex items-center justify-between text-sm">
            <label className="inline-flex items-center gap-2 text-slate-700">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-4 w-4 accent-leaf-500" />
              아이디 저장
            </label>
            <Link to="/forgot" className="text-leaf-700 hover:underline">아이디·비밀번호 찾기</Link>
          </div>
          <Button type="submit" full disabled={busy}>{busy ? <><Spinner /> 확인 중…</> : '로그인'}</Button>
        </div>
        {demoOn && (
          <div className="mt-5 rounded-xl border border-leaf-100 bg-leaf-50 p-4">
            <p className="text-sm font-semibold text-leaf-800">계정 없이 먼저 보고 싶다면</p>
            <p className="mt-1 text-xs text-slate-600">조회 전용으로 농가 화면을 둘러봅니다. 장치 제어·설정 변경은 잠겨 있습니다.</p>
            <div className="mt-3"><Button type="button" variant="secondary" full disabled={busy} onClick={tryDemo}>로그인 없이 둘러보기</Button></div>
          </div>
        )}
        <div className="mt-6 border-t border-slate-100 pt-5 text-center text-sm text-slate-600">
          처음 오셨나요? <Link to="/signup" className="inline-block py-1 font-semibold text-leaf-700 hover:underline">회원가입 신청</Link>
        </div>
        <p className="mt-4 text-xs text-slate-500">비밀번호를 5번 연속 틀리면 계정이 10분 동안 잠깁니다. 공용 PC에서는 아이디 저장을 끄세요.</p>
      </form>
    </AuthShell>
  );
}
