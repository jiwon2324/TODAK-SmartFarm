import { useEffect } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { PasswordCard } from '../Account';
import { homeOf, useAuth } from '../../hooks/auth';
import { AuthShell } from './AuthShell';

/** 관리자가 비밀번호를 초기화한 계정의 첫 로그인: 새 비밀번호로 바꾸기 전에는 다른 화면으로 가지 않는다 */
export default function PasswordRequired() {
  const { me, logout } = useAuth();
  const nav = useNavigate();
  useEffect(() => {
    document.title = '비밀번호 변경 · TODAK';
  }, []);
  if (!me) return <Navigate to="/login" replace />;
  if (!me.mustChangePassword) return <Navigate to={homeOf(me)} replace />;
  return (
    <AuthShell>
      <PasswordCard required />
      <button className="mt-4 w-full text-center text-sm text-slate-600 underline" onClick={async () => { await logout(); nav('/login'); }}>
        나중에 하기 (로그아웃)
      </button>
    </AuthShell>
  );
}
