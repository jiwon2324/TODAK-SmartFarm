import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Notice, Spinner } from '../../components/ui';
import { homeOf, useAuth } from '../../hooks/auth';
import { AuthShell } from './AuthShell';

/** /demo — 링크만 누르면 조회 전용 계정으로 바로 들어간다 (로그인 없이 둘러보기) */
export default function Demo() {
  const { demo } = useAuth();
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    demo().then((m) => nav(homeOf(m), { replace: true })).catch((e: Error) => setErr(e.message));
  }, [demo, nav]);

  return (
    <AuthShell>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-2xl font-bold text-slate-900">둘러보기</h2>
        {err ? (
          <div className="mt-4">
            <Notice tone="error">{err}</Notice>
            <Link to="/login" className="text-leaf-700 hover:underline">로그인 화면으로</Link>
          </div>
        ) : (
          <p className="mt-3 flex items-center gap-2 text-slate-600"><Spinner /> 조회 전용 계정으로 들어가는 중…</p>
        )}
      </div>
    </AuthShell>
  );
}
