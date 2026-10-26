import { passwordRules, strength } from './password';

/** 비밀번호 강도 막대 + 규칙 체크리스트 (입력하는 동안 실시간 표시) */
export function PasswordMeter({ pw, loginId }: { pw: string; loginId: string }) {
  if (!pw) return null;
  const st = strength(pw, loginId);
  const colors = ['bg-slate-200', 'bg-red-500', 'bg-amber-500', 'bg-leaf-500', 'bg-leaf-700'];
  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1">
          {[1, 2, 3, 4].map((i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= st.score ? colors[st.score] : 'bg-slate-200'}`} />)}
        </div>
        <span className="w-20 text-right text-xs text-slate-600">{st.label}</span>
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
        {passwordRules(pw, loginId).map((r) => (
          <li key={r.key} className={r.ok ? 'text-leaf-700' : 'text-slate-500'}>{r.ok ? '✓' : '·'} {r.label}</li>
        ))}
      </ul>
    </div>
  );
}
