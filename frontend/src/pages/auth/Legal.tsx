import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AuthShell } from './AuthShell';
import { DRAFT_NOTE, NOTIFY_TEXT, PRIVACY_ITEMS, TERMS } from './legalText';

/** 이용약관·개인정보처리방침 (과제용 초안) */
export default function Legal({ kind }: { kind: 'terms' | 'privacy' }) {
  const title = kind === 'terms' ? '이용약관' : '개인정보처리방침';
  useEffect(() => {
    document.title = `${title} · TODAK`;
  }, [title]);
  return (
    <AuthShell wide>
      <article className="rounded-2xl border border-slate-200 bg-white p-6 text-sm leading-relaxed text-slate-700 shadow-sm sm:p-8">
        <h2 className="text-2xl font-bold text-slate-900">{title}</h2>
        <p className="mt-1 text-xs text-amber-800">{DRAFT_NOTE}</p>
        {kind === 'terms' ? (
          <div className="mt-5 space-y-3">{TERMS.map((t) => <section key={t.h}><h3 className="font-semibold text-slate-900">{t.h}</h3><p>{t.p}</p></section>)}</div>
        ) : (
          <div className="mt-5 space-y-4">
            <section>
              <h3 className="font-semibold text-slate-900">1. 수집 항목과 이용 목적, 보유 기간</h3>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[480px] text-left text-xs">
                  <thead><tr className="border-b text-slate-600"><th className="py-1.5 pr-2">항목</th><th className="pr-2">목적</th><th className="pr-2">보유 기간</th><th>구분</th></tr></thead>
                  <tbody>{PRIVACY_ITEMS.map((x) => (
                    <tr key={x.item} className="border-b border-slate-100 align-top"><td className="py-1.5 pr-2">{x.item}</td><td className="pr-2">{x.purpose}</td><td className="pr-2">{x.keep}</td><td>{x.required ? '필수' : '선택'}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </section>
            <section><h3 className="font-semibold text-slate-900">2. 안전성 확보 조치</h3>
              <p>비밀번호는 BCrypt로 단방향 암호화해 저장하고, 로그인 유지 토큰은 HttpOnly 쿠키에 담아 스크립트가 읽을 수 없게 합니다. 5번 연속 로그인 실패 시 10분 동안 잠그며, 관리자 화면 접근과 설정 변경은 기록으로 남깁니다.</p></section>
            <section><h3 className="font-semibold text-slate-900">3. 제3자 제공·위탁</h3><p>수집한 개인정보를 제3자에게 제공하거나 처리를 위탁하지 않습니다.</p></section>
            <section><h3 className="font-semibold text-slate-900">4. 알림 수신(선택)</h3><p>{NOTIFY_TEXT}</p></section>
            <section><h3 className="font-semibold text-slate-900">5. 이용자의 권리</h3><p>내 정보 화면에서 이름·연락처·이메일을 고칠 수 있고, 운영 관리자에게 열람·정정·삭제(탈퇴)를 요청할 수 있습니다.</p></section>
          </div>
        )}
        <div className="mt-6"><Link to="/login" className="text-leaf-700 hover:underline">← 돌아가기</Link></div>
      </article>
    </AuthShell>
  );
}
