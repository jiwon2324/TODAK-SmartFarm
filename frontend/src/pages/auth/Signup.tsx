import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { get, post } from '../../api/client';
import { EMAIL_RE, formatPhone, LOGIN_ID_RE, passwordRules, PHONE_RE } from '../../components/password';
import { PasswordMeter } from '../../components/PasswordMeter';
import { Button, FormField, Notice, PasswordInput, Spinner, inputCls } from '../../components/ui';
import { AuthShell } from './AuthShell';
import { DRAFT_NOTE, NOTIFY_TEXT, PRIVACY_ITEMS, TERMS } from './legalText';

type Step = 1 | 2 | 3;
const STEPS = ['약관 동의', '정보 입력', '신청 완료'];

/**
 * 회원가입 신청 (SCR-01 확장) [REQ-F-12]. 가입해도 바로 쓰지 않고, 관리자가 본인 확인 후 역할·농장 권한을 정해 승인한다.
 * 화면 검사(아이디 형식·중복, 비밀번호 규칙, 휴대폰 형식)는 안내용이며 최종 검사는 서버가 한다.
 */
export default function Signup() {
  const [step, setStep] = useState<Step>(1);
  const [agree, setAgree] = useState({ terms: false, privacy: false, notify: false });
  const [f, setF] = useState({ loginId: '', password: '', passwordConfirm: '', name: '', phone: '', email: '', requestedRole: 'FARMER', signupNote: '' });
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [idCheck, setIdCheck] = useState<{ id: string; available: boolean; message: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openTerm, setOpenTerm] = useState<string | null>(null);
  const top = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.title = '회원가입 · TODAK';
  }, []);
  useEffect(() => {
    top.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }, [step]);

  // 아이디 입력이 멈추면 자동으로 중복 확인 (0.5초)
  useEffect(() => {
    if (!LOGIN_ID_RE.test(f.loginId)) return;
    const t = setTimeout(() => checkId(f.loginId), 500);
    return () => clearTimeout(t);
  }, [f.loginId]);

  const checkId = async (id: string) => {
    setChecking(true);
    try {
      const r = await get<{ available: boolean; message: string }>(`/api/auth/check-id?loginId=${encodeURIComponent(id)}`);
      setIdCheck({ id, ...r });
    } catch (e) {
      setIdCheck({ id, available: false, message: (e as Error).message });
    } finally {
      setChecking(false);
    }
  };

  const errors = useMemo(() => {
    const e: Record<string, string | null> = {};
    e.loginId = !f.loginId ? '아이디를 입력하세요.' : !LOGIN_ID_RE.test(f.loginId) ? '영문 소문자로 시작하는 4~20자(영문 소문자·숫자·밑줄)로 입력하세요.'
      : idCheck?.id === f.loginId && !idCheck.available ? idCheck.message : null;
    e.password = !f.password ? '비밀번호를 입력하세요.' : passwordRules(f.password, f.loginId).every((r) => r.ok) ? null : '아래 규칙을 모두 만족해야 합니다.';
    e.passwordConfirm = !f.passwordConfirm ? '비밀번호를 한 번 더 입력하세요.' : f.passwordConfirm !== f.password ? '비밀번호가 일치하지 않습니다.' : null;
    e.name = !f.name.trim() ? '이름을 입력하세요.' : f.name.length > 30 ? '30자 이내로 입력하세요.' : null;
    e.phone = !f.phone ? '휴대폰 번호를 입력하세요.' : !PHONE_RE.test(f.phone) ? '010-1234-5678 형식으로 입력하세요.' : null;
    e.email = f.email && !EMAIL_RE.test(f.email) ? '이메일 형식이 올바르지 않습니다.' : null;
    return e;
  }, [f, idCheck]);
  const idVerified = idCheck?.id === f.loginId && idCheck.available;
  const valid = Object.values(errors).every((x) => !x) && idVerified;
  const show = (k: string) => (touched[k] ? errors[k] : null);
  const allAgree = agree.terms && agree.privacy && agree.notify;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTouched({ loginId: true, password: true, passwordConfirm: true, name: true, phone: true, email: true });
    if (!valid) {
      setErr(!idVerified && !errors.loginId ? '아이디 중복 확인을 기다리는 중입니다. 잠시 후 다시 눌러 주세요.' : '입력 내용을 확인하세요.');
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await post('/api/auth/signup', { ...f, agreeTerms: agree.terms, agreePrivacy: agree.privacy, agreeNotify: agree.notify });
      setStep(3);
    } catch (e2) {
      setErr((e2 as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell wide>
      <div ref={top} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-2xl font-bold">회원가입 신청</h2>
        <ol className="mt-4 flex items-center gap-2 text-xs sm:text-sm" aria-label="가입 단계">
          {STEPS.map((s, i) => (
            <li key={s} className="flex flex-1 items-center gap-2" aria-current={step === i + 1 ? 'step' : undefined}>
              <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-semibold ${step > i + 1 ? 'bg-leaf-500 text-white' : step === i + 1 ? 'bg-leaf-700 text-white' : 'bg-slate-200 text-slate-600'}`}>
                {step > i + 1 ? '✓' : i + 1}
              </span>
              <span className={step === i + 1 ? 'font-semibold text-slate-900' : 'text-slate-500'}>{s}</span>
              {i < 2 && <span className="h-px flex-1 bg-slate-200" aria-hidden="true" />}
            </li>
          ))}
        </ol>

        {step === 1 && (
          <div className="mt-6">
            <label className="flex items-center gap-3 rounded-lg border border-slate-300 p-3 font-semibold">
              <input type="checkbox" className="h-5 w-5 accent-leaf-500" checked={allAgree}
                onChange={(e) => setAgree({ terms: e.target.checked, privacy: e.target.checked, notify: e.target.checked })} />
              전체 동의 (선택 항목 포함)
            </label>
            <div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">
              <AgreeRow label="이용약관 동의" required checked={agree.terms} onChange={(v) => setAgree({ ...agree, terms: v })}
                open={openTerm === 'terms'} onToggle={() => setOpenTerm(openTerm === 'terms' ? null : 'terms')}>
                {TERMS.map((t) => <div key={t.h} className="mb-2"><b>{t.h}</b> {t.p}</div>)}
              </AgreeRow>
              <AgreeRow label="개인정보 수집·이용 동의" required checked={agree.privacy} onChange={(v) => setAgree({ ...agree, privacy: v })}
                open={openTerm === 'privacy'} onToggle={() => setOpenTerm(openTerm === 'privacy' ? null : 'privacy')}>
                <table className="w-full text-xs">
                  <thead><tr className="text-left text-slate-600"><th className="py-1 pr-2">항목</th><th className="pr-2">목적</th><th>보유 기간</th></tr></thead>
                  <tbody>{PRIVACY_ITEMS.map((x) => (
                    <tr key={x.item} className="border-t border-slate-100 align-top"><td className="py-1 pr-2">{x.item}{!x.required && ' (선택)'}</td><td className="pr-2">{x.purpose}</td><td>{x.keep}</td></tr>
                  ))}</tbody>
                </table>
                <p className="mt-2">동의를 거부할 수 있으나, 필수 항목에 동의하지 않으면 가입할 수 없습니다.</p>
              </AgreeRow>
              <AgreeRow label="농장 알림 수신 동의" checked={agree.notify} onChange={(v) => setAgree({ ...agree, notify: v })}
                open={openTerm === 'notify'} onToggle={() => setOpenTerm(openTerm === 'notify' ? null : 'notify')}>
                {NOTIFY_TEXT}
              </AgreeRow>
            </div>
            <p className="mt-2 text-xs text-slate-500">{DRAFT_NOTE}</p>
            <div className="mt-6 flex gap-2">
              <Link to="/login" className="flex-1 rounded-lg px-4 py-2.5 text-center text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50">취소</Link>
              <div className="flex-1"><Button full disabled={!agree.terms || !agree.privacy} onClick={() => setStep(2)}>다음</Button></div>
            </div>
          </div>
        )}

        {step === 2 && (
          <form onSubmit={submit} noValidate className="mt-6 space-y-4">
            <Notice tone="error">{err}</Notice>
            <FormField id="su-id" label="아이디" required error={show('loginId')}
              ok={idVerified ? idCheck?.message : null} hint={checking ? '확인 중…' : '영문 소문자로 시작, 4~20자 (영문 소문자·숫자·밑줄)'}>
              <input id="su-id" className={`${inputCls} ${show('loginId') ? 'border-red-400' : ''}`} value={f.loginId} autoComplete="username"
                autoCapitalize="none" spellCheck={false} aria-describedby="su-id-msg" aria-invalid={!!show('loginId') || undefined}
                onChange={(e) => setF({ ...f, loginId: e.target.value.toLowerCase().trim() })} onBlur={() => setTouched({ ...touched, loginId: true })} />
            </FormField>
            <FormField id="su-pw" label="비밀번호" required error={show('password')}>
              <PasswordInput id="su-pw" value={f.password} onChange={(v) => setF({ ...f, password: v })} autoComplete="new-password"
                invalid={!!show('password')} onBlur={() => setTouched({ ...touched, password: true })} />
              <PasswordMeter pw={f.password} loginId={f.loginId} />
            </FormField>
            <FormField id="su-pw2" label="비밀번호 확인" required error={show('passwordConfirm')}
              ok={f.passwordConfirm && f.passwordConfirm === f.password ? '비밀번호가 일치합니다.' : null}>
              <PasswordInput id="su-pw2" value={f.passwordConfirm} onChange={(v) => setF({ ...f, passwordConfirm: v })} autoComplete="new-password"
                invalid={!!show('passwordConfirm')} onBlur={() => setTouched({ ...touched, passwordConfirm: true })} />
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField id="su-name" label="이름" required error={show('name')}>
                <input id="su-name" className={inputCls} value={f.name} autoComplete="name" maxLength={30} aria-describedby="su-name-msg"
                  onChange={(e) => setF({ ...f, name: e.target.value })} onBlur={() => setTouched({ ...touched, name: true })} />
              </FormField>
              <FormField id="su-phone" label="휴대폰 번호" required error={show('phone')} hint="본인 확인과 비밀번호 초기화에 씁니다.">
                <input id="su-phone" className={inputCls} value={f.phone} inputMode="numeric" autoComplete="tel" placeholder="010-0000-0000"
                  aria-describedby="su-phone-msg" onChange={(e) => setF({ ...f, phone: formatPhone(e.target.value) })} onBlur={() => setTouched({ ...touched, phone: true })} />
              </FormField>
            </div>
            <FormField id="su-email" label="이메일 (선택)" error={show('email')}>
              <input id="su-email" type="email" className={inputCls} value={f.email} autoComplete="email" aria-describedby="su-email-msg"
                onChange={(e) => setF({ ...f, email: e.target.value.trim() })} onBlur={() => setTouched({ ...touched, email: true })} />
            </FormField>
            <fieldset className="text-sm">
              <legend className="mb-1 font-medium text-slate-700">가입 유형<span className="ml-0.5 text-red-600">*</span></legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {[{ v: 'FARMER', t: '농가 사용자', d: '내 농장 확인과 장치 제어' }, { v: 'VIEWER', t: '조회 전용', d: '검수자·컨설턴트: 보기만 가능' }].map((o) => (
                  <label key={o.v} className={`cursor-pointer rounded-lg border p-3 ${f.requestedRole === o.v ? 'border-leaf-500 bg-leaf-50' : 'border-slate-300'}`}>
                    <input type="radio" name="role" value={o.v} className="sr-only" checked={f.requestedRole === o.v} onChange={() => setF({ ...f, requestedRole: o.v })} />
                    <div className="font-semibold">{o.t}</div>
                    <div className="text-xs text-slate-600">{o.d}</div>
                  </label>
                ))}
              </div>
            </fieldset>
            <FormField id="su-note" label="농장 정보·요청 사항 (선택)" hint={`${f.signupNote.length}/300 · 예: 양평군 ○○면 하우스 1동, 농장주 김○○`}>
              <textarea id="su-note" rows={3} maxLength={300} className={inputCls} value={f.signupNote} aria-describedby="su-note-msg"
                onChange={(e) => setF({ ...f, signupNote: e.target.value })} />
            </FormField>
            <div className="flex gap-2 pt-2">
              <div className="flex-1"><Button variant="secondary" full onClick={() => setStep(1)}>이전</Button></div>
              <div className="flex-1"><Button type="submit" full disabled={busy}>{busy ? <><Spinner /> 신청 중…</> : '가입 신청'}</Button></div>
            </div>
          </form>
        )}

        {step === 3 && (
          <div className="mt-8 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-leaf-50 text-2xl text-leaf-700" aria-hidden="true">✓</div>
            <h3 className="mt-4 text-xl font-bold">가입 신청이 접수되었습니다</h3>
            <p className="mt-2 text-sm text-slate-600"><b>{f.loginId}</b> 계정은 관리자 승인 후 사용할 수 있습니다.</p>
            <ol className="mx-auto mt-5 max-w-sm space-y-2 text-left text-sm text-slate-700">
              <li><b>1.</b> 관리자가 휴대폰으로 본인 여부를 확인합니다.</li>
              <li><b>2.</b> 농장을 연결하고 권한(농가/조회 전용)을 정해 승인합니다.</li>
              <li><b>3.</b> 승인되면 같은 아이디와 비밀번호로 로그인합니다.</li>
            </ol>
            <Link to="/login" className="mt-6 inline-block rounded-lg bg-leaf-500 px-6 py-2.5 text-sm font-medium text-white hover:bg-leaf-600">로그인 화면으로</Link>
          </div>
        )}
      </div>
      {step !== 3 && <p className="mt-4 text-center text-sm text-slate-600">이미 계정이 있나요? <Link to="/login" className="font-semibold text-leaf-700 hover:underline">로그인</Link></p>}
    </AuthShell>
  );
}

function AgreeRow({ label, required, checked, onChange, open, onToggle, children }: {
  label: string; required?: boolean; checked: boolean; onChange: (v: boolean) => void; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <div className="p-3">
      <div className="flex items-center gap-3">
        <input type="checkbox" className="h-5 w-5 accent-leaf-500" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
        <span className="flex-1 text-sm"><span className={required ? 'text-leaf-700' : 'text-slate-500'}>[{required ? '필수' : '선택'}]</span> {label}</span>
        <button type="button" onClick={onToggle} aria-expanded={open} className="text-xs text-slate-600 underline">{open ? '접기' : '보기'}</button>
      </div>
      {open && <div className="mt-2 max-h-48 overflow-y-auto rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">{children}</div>}
    </div>
  );
}
