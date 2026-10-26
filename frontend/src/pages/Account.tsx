import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { patch, post } from '../api/client';
import { fmtTime } from '../components/format';
import { EMAIL_RE, formatPhone, passwordRules, PHONE_RE, ROLE_LABEL } from '../components/password';
import { PasswordMeter } from '../components/PasswordMeter';
import { Button, Card, ConfirmDialog, FormField, Notice, PageTitle, PasswordInput, Spinner, inputCls } from '../components/ui';
import { useAuth } from '../hooks/auth';

/** 내 정보: 프로필 수정, 비밀번호 변경, 로그인 보안(최근 로그인·모든 기기 로그아웃) [REQ-F-12] */
export default function Account() {
  const { me, reload, logout } = useAuth();
  const nav = useNavigate();
  const [p, setP] = useState({ name: me?.name ?? '', phone: me?.phone ?? '', email: me?.email ?? '', notifyAgreed: !!me?.notifyAgreed });
  const [pMsg, setPMsg] = useState<{ tone: 'ok' | 'error'; msg: string } | null>(null);
  const [askAll, setAskAll] = useState(false);

  useEffect(() => {
    document.title = '내 정보 · TODAK';
  }, []);

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    if (!p.name.trim() || (p.phone && !PHONE_RE.test(p.phone)) || (p.email && !EMAIL_RE.test(p.email))) {
      setPMsg({ tone: 'error', msg: '이름, 휴대폰(010-0000-0000), 이메일 형식을 확인하세요.' });
      return;
    }
    try {
      await patch('/api/auth/me', { ...p, phone: p.phone || null, email: p.email || null });
      await reload();
      setPMsg({ tone: 'ok', msg: '내 정보를 저장했습니다.' });
    } catch (e2) {
      setPMsg({ tone: 'error', msg: (e2 as Error).message });
    }
  };

  const logoutAll = async () => {
    setAskAll(false);
    await post('/api/auth/logout-all', {}, { 'X-TODAK-CSRF': '1' });
    await logout();
    nav('/login', { replace: true, state: { flash: '모든 기기에서 로그아웃했습니다.' } });
  };

  if (!me) return null;
  return (
    <div className="max-w-3xl">
      <PageTitle title="내 정보" desc={`${me.loginId} · ${ROLE_LABEL[me.role]} · 가입 ${fmtTime(me.createdAt)}`} />
      <div className="grid gap-4">
        <Card title="기본 정보">
          <form onSubmit={saveProfile} className="space-y-4" noValidate>
            <Notice tone={pMsg?.tone ?? 'info'}>{pMsg?.msg}</Notice>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField id="ac-name" label="이름" required>
                <input id="ac-name" className={inputCls} value={p.name} maxLength={30} onChange={(e) => setP({ ...p, name: e.target.value })} />
              </FormField>
              <FormField id="ac-phone" label="휴대폰 번호">
                <input id="ac-phone" className={inputCls} value={p.phone} inputMode="numeric" onChange={(e) => setP({ ...p, phone: formatPhone(e.target.value) })} />
              </FormField>
            </div>
            <FormField id="ac-email" label="이메일">
              <input id="ac-email" type="email" className={inputCls} value={p.email} onChange={(e) => setP({ ...p, email: e.target.value.trim() })} />
            </FormField>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4 accent-leaf-500" checked={p.notifyAgreed} onChange={(e) => setP({ ...p, notifyAgreed: e.target.checked })} />
              농장 알림 수신 동의 (선택)
            </label>
            <p className="text-xs text-slate-500">역할과 농장 접근 권한은 운영 관리자만 바꿀 수 있습니다. 접근 농장: {me.farmIds.length ? me.farmIds.join(', ') + '번' : '없음'}</p>
            <Button type="submit">저장</Button>
          </form>
        </Card>
        <PasswordCard />
        <Card title="로그인 보안">
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-slate-500">최근 로그인</dt><dd>{fmtTime(me.lastLoginAt)}</dd></div>
            <div><dt className="text-slate-500">비밀번호 변경일</dt><dd>{fmtTime(me.pwChangedAt)}</dd></div>
          </dl>
          <p className="mt-3 text-sm text-slate-600">다른 기기(공용 PC 등)에서 로그인한 채로 두었다면 모든 기기에서 로그아웃하세요.</p>
          <div className="mt-3"><Button variant="secondary" onClick={() => setAskAll(true)}>모든 기기에서 로그아웃</Button></div>
        </Card>
      </div>
      <ConfirmDialog open={askAll} title="모든 기기에서 로그아웃" body="이 기기를 포함해 이 계정으로 로그인된 모든 곳의 로그인이 끊깁니다." confirmLabel="로그아웃"
        onConfirm={logoutAll} onCancel={() => setAskAll(false)} />
    </div>
  );
}

/** 비밀번호 변경 카드 (내 정보, 최초 로그인 강제 변경 화면 공용) */
export function PasswordCard({ required, onDone }: { required?: boolean; onDone?: () => void }) {
  const { me, adoptToken } = useAuth();
  const [f, setF] = useState({ current: '', next: '', confirm: '' });
  const [msg, setMsg] = useState<{ tone: 'ok' | 'error'; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const rulesOk = passwordRules(f.next, me?.loginId ?? '').every((r) => r.ok);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!f.current || !rulesOk || f.next !== f.confirm) {
      setMsg({ tone: 'error', msg: !f.current ? '현재 비밀번호를 입력하세요.' : !rulesOk ? '새 비밀번호가 규칙을 만족하지 않습니다.' : '새 비밀번호 확인이 일치하지 않습니다.' });
      return;
    }
    setBusy(true);
    try {
      const r = await post<{ accessToken: string }>('/api/auth/password', { currentPassword: f.current, newPassword: f.next });
      await adoptToken(r.accessToken);
      setF({ current: '', next: '', confirm: '' });
      setMsg({ tone: 'ok', msg: '비밀번호를 바꿨습니다. 다른 기기의 로그인은 모두 끊겼습니다.' });
      onDone?.();
    } catch (e2) {
      setMsg({ tone: 'error', msg: (e2 as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="비밀번호 변경">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {required && <Notice tone="warn">관리자가 정한 임시 비밀번호로 로그인했습니다. 계속하려면 새 비밀번호로 바꾸세요.</Notice>}
        <Notice tone={msg?.tone ?? 'info'}>{msg?.msg}</Notice>
        <FormField id="pw-cur" label={required ? '임시 비밀번호' : '현재 비밀번호'} required>
          <PasswordInput id="pw-cur" value={f.current} onChange={(v) => setF({ ...f, current: v })} autoComplete="current-password" />
        </FormField>
        <FormField id="pw-new" label="새 비밀번호" required>
          <PasswordInput id="pw-new" value={f.next} onChange={(v) => setF({ ...f, next: v })} autoComplete="new-password" />
          <PasswordMeter pw={f.next} loginId={me?.loginId ?? ''} />
        </FormField>
        <FormField id="pw-new2" label="새 비밀번호 확인" required
          error={f.confirm && f.confirm !== f.next ? '일치하지 않습니다.' : null} ok={f.confirm && f.confirm === f.next ? '일치합니다.' : null}>
          <PasswordInput id="pw-new2" value={f.confirm} onChange={(v) => setF({ ...f, confirm: v })} autoComplete="new-password" />
        </FormField>
        <Button type="submit" disabled={busy}>{busy ? <><Spinner /> 변경 중…</> : '비밀번호 변경'}</Button>
      </form>
    </Card>
  );
}
