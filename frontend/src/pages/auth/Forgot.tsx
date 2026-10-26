import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { post } from '../../api/client';
import { Button, FormField, Notice, Spinner, inputCls } from '../../components/ui';
import { formatPhone, PHONE_RE } from '../../components/password';
import { AuthShell } from './AuthShell';

/**
 * 아이디·비밀번호 찾기. 이메일·문자 발송 수단이 없으므로(SMS는 확장 범위) 본인 확인 정보를 받아 관리자에게 초기화 요청을 남긴다.
 * 계정 존재 여부가 드러나지 않도록 결과와 상관없이 같은 안내를 보여 준다.
 */
export default function Forgot() {
  const [f, setF] = useState({ loginId: '', name: '', phone: '' });
  const [done, setDone] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.title = '아이디·비밀번호 찾기 · TODAK';
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!f.loginId || !f.name || !PHONE_RE.test(f.phone)) {
      setErr('아이디, 이름, 휴대폰 번호를 정확히 입력하세요.');
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const r = await post<{ message: string }>('/api/auth/password-reset-request', f);
      setDone(r.message);
    } catch (e2) {
      setErr((e2 as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-2xl font-bold">아이디·비밀번호 찾기</h2>
        {done ? (
          <>
            <Notice tone="ok" className="mt-5">{done}</Notice>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
              <li>관리자가 요청을 확인하고 본인 여부를 전화로 확인합니다.</li>
              <li>임시 비밀번호를 받으면 로그인 후 곧바로 새 비밀번호로 바꿉니다.</li>
            </ol>
            <Link to="/login" className="mt-6 block rounded-lg bg-leaf-500 px-4 py-2.5 text-center text-sm font-medium text-white hover:bg-leaf-600">로그인으로 돌아가기</Link>
          </>
        ) : (
          <form onSubmit={submit} noValidate>
            <p className="mt-1 text-sm text-slate-600">가입할 때 입력한 정보를 적으면 관리자에게 비밀번호 초기화 요청이 전달됩니다.</p>
            <div className="mt-5"><Notice tone="error">{err}</Notice></div>
            <div className="space-y-4">
              <FormField id="fg-id" label="아이디" required hint="아이디가 기억나지 않으면 아래 관리자 문의를 이용하세요.">
                <input id="fg-id" className={inputCls} value={f.loginId} onChange={(e) => setF({ ...f, loginId: e.target.value })} autoComplete="username" />
              </FormField>
              <FormField id="fg-name" label="이름" required>
                <input id="fg-name" className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} autoComplete="name" />
              </FormField>
              <FormField id="fg-phone" label="휴대폰 번호" required>
                <input id="fg-phone" className={inputCls} inputMode="numeric" value={f.phone} placeholder="010-0000-0000"
                  onChange={(e) => setF({ ...f, phone: formatPhone(e.target.value) })} autoComplete="tel" />
              </FormField>
              <Button type="submit" full disabled={busy}>{busy ? <><Spinner /> 요청 중…</> : '초기화 요청'}</Button>
            </div>
            <div className="mt-6 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
              <b>아이디를 잊으셨나요?</b> 농장 운영 관리자에게 이름과 휴대폰 번호로 문의하세요. (관리자 연락처는 농장별로 안내 · 시범 운영 단계)
            </div>
            <div className="mt-4 text-center text-sm"><Link to="/login" className="text-leaf-700 hover:underline">로그인으로 돌아가기</Link></div>
          </form>
        )}
      </div>
    </AuthShell>
  );
}
