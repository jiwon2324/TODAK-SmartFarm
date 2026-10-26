import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Button, ErrorBox, Field, inputCls } from '../components/ui';
import { useAuth } from '../hooks/auth';

/** SCR-01 로그인 [REQ-F-12] */
export default function Login() {
  const { me, login } = useAuth();
  const nav = useNavigate();
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (me) return <Navigate to={me.role === 'ADMIN' ? '/admin' : '/farm'} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!loginId || !password) {
      setError('아이디와 비밀번호를 입력하세요');
      return;
    }
    setBusy(true);
    try {
      const m = await login(loginId, password);
      nav(m.role === 'ADMIN' ? '/admin' : '/farm');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-leaf-50 to-white p-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 text-center">
          <div className="text-3xl font-extrabold text-leaf-700">TODAK</div>
          <div className="mt-1 text-sm text-slate-500">양평 방울토마토 스마트 농업 정보시스템</div>
        </div>
        <ErrorBox msg={error} />
        <div className="space-y-3">
          <Field label="아이디">
            <input className={inputCls} value={loginId} onChange={(e) => setLoginId(e.target.value)} autoComplete="username" />
          </Field>
          <Field label="비밀번호">
            <input className={inputCls} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </Field>
        </div>
        <div className="mt-5">
          <Button type="submit" disabled={busy}>{busy ? '로그인 중…' : '로그인'}</Button>
        </div>
        <p className="mt-4 text-xs text-slate-400">5회 실패하면 10분 동안 잠깁니다. 테스트 계정은 README를 참고하세요.</p>
      </form>
    </div>
  );
}
