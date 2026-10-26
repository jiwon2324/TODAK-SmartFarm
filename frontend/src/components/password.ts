// 비밀번호·아이디 규칙 — 백엔드 kr.todak.auth.PasswordPolicy와 같은 규칙 (화면에서 미리 안내, 최종 검사는 서버)

export const LOGIN_ID_RE = /^[a-z][a-z0-9_]{3,19}$/;

export interface Rule {
  key: string;
  label: string;
  ok: boolean;
}

export function passwordRules(pw: string, loginId: string): Rule[] {
  return [
    { key: 'len', label: '8~64자', ok: pw.length >= 8 && pw.length <= 64 },
    { key: 'letter', label: '영문 포함', ok: /[A-Za-z]/.test(pw) },
    { key: 'digit', label: '숫자 포함', ok: /[0-9]/.test(pw) },
    { key: 'special', label: '특수문자 포함', ok: /[^A-Za-z0-9\s]/.test(pw) },
    { key: 'space', label: '공백 없음', ok: pw.length > 0 && !/\s/.test(pw) },
    { key: 'id', label: '아이디 미포함', ok: pw.length > 0 && (!loginId || !pw.toLowerCase().includes(loginId.toLowerCase())) },
    { key: 'repeat', label: '같은 문자 4번 연속 금지', ok: pw.length > 0 && !/(.)\1{3,}/.test(pw) },
  ];
}

/** 0~4 강도 (규칙 충족 + 길이·문자 종류 다양성) */
export function strength(pw: string, loginId: string): { score: number; label: string } {
  if (!pw) return { score: 0, label: '' };
  const rules = passwordRules(pw, loginId);
  if (!rules.every((r) => r.ok)) return { score: 1, label: '규칙 미충족' };
  let s = 2;
  if (pw.length >= 12) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  return { score: Math.min(s, 4), label: ['', '규칙 미충족', '보통', '좋음', '강함'][Math.min(s, 4)] };
}

export function formatPhone(v: string) {
  const d = v.replace(/\D/g, '').slice(0, 11);
  if (d.length < 4) return d;
  if (d.length < 8) return `${d.slice(0, 3)}-${d.slice(3)}`;
  return d.length === 11 ? `${d.slice(0, 3)}-${d.slice(3, 7)}-${d.slice(7)}` : `${d.slice(0, 3)}-${d.slice(3, 6)}-${d.slice(6)}`;
}

export const PHONE_RE = /^01[016789]-?\d{3,4}-?\d{4}$/;
export const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** 관리자 임시 비밀번호: 규칙을 만족하는 12자 난수 */
export function tempPassword() {
  const pick = (set: string, n: number) => Array.from(crypto.getRandomValues(new Uint32Array(n)), (x) => set[x % set.length]).join('');
  const raw = pick('ABCDEFGHJKLMNPQRSTUVWXYZ', 2) + pick('abcdefghijkmnpqrstuvwxyz', 5) + pick('23456789', 3) + pick('!@#$%^&*', 2);
  return raw.split('').sort(() => crypto.getRandomValues(new Uint8Array(1))[0] - 128).join('');
}

export const ROLE_LABEL: Record<string, string> = { ADMIN: '관리자', FARMER: '농가', VIEWER: '조회 전용' };
