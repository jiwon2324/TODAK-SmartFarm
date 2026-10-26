import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { get, patch, post, put } from '../../api/client';
import type { AdminUser, Role } from '../../api/types';
import { fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { formatPhone, passwordRules, ROLE_LABEL, tempPassword } from '../../components/password';
import { Badge, Button, Card, ConfirmDialog, Empty, FormField, Modal, Notice, PageTitle, Table, inputCls } from '../../components/ui';

type Tab = 'all' | 'pending' | 'reset';

/**
 * SCR-A2 사용자 관리 [REQ-F-12]: 가입 신청 승인·거절(역할·농장 지정), 비밀번호 초기화 요청 처리(임시 비밀번호 → 첫 로그인 때 변경),
 * 역할(관리자·농가·조회 전용)·활성/비활성·잠금 해제·농장 접근 권한, 관리자 직접 등록
 */
export default function Users() {
  const { farms } = useFarm();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [tab, setTab] = useState<Tab>('all');
  const [q, setQ] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [approve, setApprove] = useState<{ u: AdminUser; role: Role; farmIds: number[] } | null>(null);
  const [reject, setReject] = useState<AdminUser | null>(null);
  const [temp, setTemp] = useState<{ u: AdminUser; pw: string; done: boolean } | null>(null);
  const [form, setForm] = useState({ loginId: '', password: tempPassword(), name: '', phone: '', role: 'FARMER' as Role, farmIds: [] as number[] });

  const load = useCallback(async () => {
    try {
      setUsers(await get<AdminUser[]>('/api/admin/users'));
    } catch (e) {
      setErr((e as Error).message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      setMsg(ok);
      setErr(null);
      await load();
      return true;
    } catch (e) {
      setErr((e as Error).message);
      setMsg(null);
      return false;
    }
  };

  const pending = useMemo(() => users.filter((u) => u.approvalStatus === 'PENDING'), [users]);
  const resets = useMemo(() => users.filter((u) => u.pwResetRequestedAt), [users]);
  const shown = useMemo(() => {
    const base = tab === 'pending' ? pending : tab === 'reset' ? resets : users;
    const k = q.trim().toLowerCase();
    return k ? base.filter((u) => `${u.loginId} ${u.name} ${u.phone ?? ''}`.toLowerCase().includes(k)) : base;
  }, [users, tab, q, pending, resets]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    const pw = form.password;
    if (await act(() => post('/api/admin/users', form), `${form.loginId} 계정을 만들었습니다. 임시 비밀번호 ${pw} 를 본인에게 전달하세요 (첫 로그인 때 변경).`)) {
      setForm({ loginId: '', password: tempPassword(), name: '', phone: '', role: 'FARMER', farmIds: [] });
    }
  };

  const toggleFarm = (u: AdminUser, f: number) => {
    const next = u.farmIds.includes(f) ? u.farmIds.filter((x) => x !== f) : [...u.farmIds, f];
    act(() => put(`/api/admin/users/${u.userId}/farms`, next), `${u.loginId}의 농장 권한을 바꿨습니다.`);
  };

  const status = (u: AdminUser) => {
    if (u.approvalStatus === 'PENDING') return <Badge tone="amber">승인 대기</Badge>;
    if (u.approvalStatus === 'REJECTED') return <Badge tone="gray">거절</Badge>;
    if (!u.isActive) return <Badge tone="gray">사용 중지</Badge>;
    if (u.lockedUntil && new Date(u.lockedUntil) > new Date()) return <Badge tone="red">잠김</Badge>;
    return <Badge tone="green">사용 중</Badge>;
  };

  return (
    <div>
      <PageTitle title="사용자 관리" desc="농가·조회 전용 사용자는 연결된 농장의 데이터만 볼 수 있습니다. 사용 중지하면 즉시 모든 로그인이 끊깁니다." />
      <Notice tone="error">{err}</Notice>
      <Notice tone="ok">{msg}</Notice>
      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title={
          <div className="flex flex-wrap gap-1" role="tablist" aria-label="사용자 구분">
            {([['all', `전체 ${users.length}`], ['pending', `가입 승인 대기 ${pending.length}`], ['reset', `초기화 요청 ${resets.length}`]] as [Tab, string][]).map(([k, l]) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                className={`rounded-full px-3 py-1 text-sm ${tab === k ? 'bg-leaf-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}>{l}</button>
            ))}
          </div>
        } action={<input aria-label="사용자 검색" placeholder="아이디·이름·연락처" className="w-40 rounded-lg border border-slate-300 px-2 py-1 text-sm" value={q} onChange={(e) => setQ(e.target.value)} />}>
          {shown.length === 0 ? <Empty>{tab === 'pending' ? '승인을 기다리는 가입 신청이 없습니다.' : tab === 'reset' ? '처리할 초기화 요청이 없습니다.' : '사용자가 없습니다.'}</Empty> : (
            <Table head={['사용자', '역할', '상태', '농장 권한', '최근 로그인', '']}>
              {shown.map((u) => (
                <tr key={u.userId} className="align-top">
                  <td className="py-2 pr-3">
                    <div className="font-medium">{u.loginId}</div>
                    <div className="text-xs text-slate-600">{u.name} · {u.phone ?? '-'}</div>
                    {u.signupNote && <div className="mt-1 max-w-[220px] text-xs text-slate-500">요청: {u.signupNote}</div>}
                    {u.pwResetRequestedAt && <div className="mt-1 text-xs text-amber-800">초기화 요청 {fmtTime(u.pwResetRequestedAt)}</div>}
                  </td>
                  <td className="pr-3">
                    {u.approvalStatus === 'APPROVED' ? (
                      <select aria-label={`${u.loginId} 역할`} className="rounded border border-slate-300 px-1 py-0.5 text-sm" value={u.role}
                        onChange={(e) => act(() => patch(`/api/admin/users/${u.userId}`, { role: e.target.value }), `${u.loginId} 역할을 ${ROLE_LABEL[e.target.value]}(으)로 바꿨습니다.`)}>
                        {(['FARMER', 'VIEWER', 'ADMIN'] as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                      </select>
                    ) : <span className="text-sm">{ROLE_LABEL[u.requestedRole ?? u.role]} 신청</span>}
                  </td>
                  <td className="pr-3">{status(u)}{u.mustChangePassword && <div className="mt-1 text-xs text-slate-500">임시 비밀번호</div>}</td>
                  <td className="pr-3">
                    {u.role === 'ADMIN' ? <span className="text-xs text-slate-500">전체</span> : u.approvalStatus !== 'APPROVED' ? '-' : farms.map((f) => (
                      <label key={f.farmId} className="mr-2 inline-flex items-center gap-1 text-xs">
                        <input type="checkbox" checked={u.farmIds.includes(f.farmId)} onChange={() => toggleFarm(u, f.farmId)} />{f.farmName}
                      </label>
                    ))}
                  </td>
                  <td className="whitespace-nowrap pr-3 text-xs">{u.lastLoginAt ? fmtTime(u.lastLoginAt) : '없음'}</td>
                  <td className="whitespace-nowrap">
                    {u.approvalStatus === 'PENDING' ? (
                      <>
                        <Button small onClick={() => setApprove({ u, role: u.requestedRole ?? 'FARMER', farmIds: [] })}>승인</Button>
                        <Button small variant="ghost" onClick={() => setReject(u)}>거절</Button>
                      </>
                    ) : u.approvalStatus === 'APPROVED' && (
                      <>
                        <Button small variant={u.pwResetRequestedAt ? 'primary' : 'ghost'} onClick={() => setTemp({ u, pw: tempPassword(), done: false })}>임시 비밀번호</Button>
                        {u.lockedUntil && new Date(u.lockedUntil) > new Date() && (
                          <Button small variant="ghost" onClick={() => act(() => patch(`/api/admin/users/${u.userId}`, { unlock: true }), `${u.loginId} 잠금을 풀었습니다.`)}>잠금 해제</Button>
                        )}
                        <Button small variant="ghost" onClick={() => act(() => patch(`/api/admin/users/${u.userId}`, { isActive: !u.isActive }), u.isActive ? `${u.loginId} 사용을 중지했습니다.` : `${u.loginId} 사용을 재개했습니다.`)}>
                          {u.isActive ? '사용 중지' : '사용 재개'}
                        </Button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="사용자 직접 등록">
          <form onSubmit={create} className="space-y-3">
            <FormField id="nu-id" label="아이디" required hint="영문 소문자로 시작 4~20자">
              <input id="nu-id" className={inputCls} value={form.loginId} onChange={(e) => setForm({ ...form, loginId: e.target.value.toLowerCase().trim() })} required />
            </FormField>
            <FormField id="nu-pw" label="임시 비밀번호" hint="첫 로그인 때 본인이 바꾸도록 설정됩니다."
              error={form.password && !passwordRules(form.password, form.loginId).every((r) => r.ok) ? '영문·숫자·특수문자 포함 8자 이상, 아이디 미포함' : null}>
              <div className="flex gap-2">
                <input id="nu-pw" className={`${inputCls} font-mono`} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
                <Button small variant="secondary" onClick={() => setForm({ ...form, password: tempPassword() })}>새로</Button>
              </div>
            </FormField>
            <FormField id="nu-name" label="이름" required>
              <input id="nu-name" className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </FormField>
            <FormField id="nu-phone" label="휴대폰">
              <input id="nu-phone" className={inputCls} value={form.phone} inputMode="numeric" onChange={(e) => setForm({ ...form, phone: formatPhone(e.target.value) })} />
            </FormField>
            <FormField id="nu-role" label="역할">
              <select id="nu-role" className={inputCls} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                {(['FARMER', 'VIEWER', 'ADMIN'] as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </FormField>
            <FarmChecks farms={farms} value={form.farmIds} onChange={(v) => setForm({ ...form, farmIds: v })} />
            <Button type="submit">등록</Button>
          </form>
        </Card>
      </div>

      <Modal open={!!approve} title="가입 신청 승인" onClose={() => setApprove(null)}>
        {approve && (
          <div className="space-y-3 text-sm">
            <div className="rounded-lg bg-slate-50 p-3">
              <div><b>{approve.u.name}</b> ({approve.u.loginId}) · {approve.u.phone}</div>
              <div className="text-slate-600">{approve.u.email ?? '이메일 없음'} · 신청 {fmtTime(approve.u.createdAt)}</div>
              {approve.u.signupNote && <div className="mt-1">요청: {approve.u.signupNote}</div>}
            </div>
            <Notice tone="info">승인 전에 휴대폰으로 본인 여부를 확인하세요.</Notice>
            <FormField id="ap-role" label="역할">
              <select id="ap-role" className={inputCls} value={approve.role} onChange={(e) => setApprove({ ...approve, role: e.target.value as Role })}>
                <option value="FARMER">농가</option><option value="VIEWER">조회 전용</option>
              </select>
            </FormField>
            <FarmChecks farms={farms} value={approve.farmIds} onChange={(v) => setApprove({ ...approve, farmIds: v })} />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setApprove(null)}>취소</Button>
              <Button disabled={approve.farmIds.length === 0} onClick={async () => {
                const a = approve;
                setApprove(null);
                await act(() => post(`/api/admin/users/${a.u.userId}/approve`, { role: a.role, farmIds: a.farmIds }), `${a.u.loginId} 가입을 승인했습니다.`);
              }}>승인</Button>
            </div>
          </div>
        )}
      </Modal>

      <Modal open={!!temp} title="임시 비밀번호 발급" onClose={() => setTemp(null)}>
        {temp && (temp.done ? (
          <div className="space-y-3 text-sm">
            <Notice tone="ok">{temp.u.loginId}의 비밀번호를 바꿨고 기존 로그인을 모두 끊었습니다.</Notice>
            <div className="rounded-lg bg-slate-50 p-3 text-center font-mono text-lg tracking-wider" aria-label="임시 비밀번호">{temp.pw}</div>
            <p className="text-slate-600">이 화면을 닫으면 다시 볼 수 없습니다. 본인 확인 후 전화나 대면으로 전달하세요. 첫 로그인 때 새 비밀번호로 바꾸게 됩니다.</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(temp.pw)}>복사</Button>
              <Button onClick={() => setTemp(null)}>닫기</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <p><b>{temp.u.name}</b> ({temp.u.loginId}, {temp.u.phone ?? '연락처 없음'})에게 임시 비밀번호를 발급합니다. 휴대폰으로 본인 여부를 먼저 확인하세요.</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setTemp(null)}>취소</Button>
              <Button onClick={async () => {
                const ok = await act(() => patch(`/api/admin/users/${temp.u.userId}`, { newPassword: temp.pw }), `${temp.u.loginId}에게 임시 비밀번호를 발급했습니다.`);
                if (ok) setTemp({ ...temp, done: true });
              }}>발급</Button>
            </div>
          </div>
        ))}
      </Modal>

      <ConfirmDialog open={!!reject} title="가입 신청 거절" danger confirmLabel="거절"
        body={reject && <>{reject.name}({reject.loginId})의 가입 신청을 거절합니다. 신청자는 로그인할 수 없습니다.</>}
        onConfirm={async () => {
          const r = reject!;
          setReject(null);
          await act(() => post(`/api/admin/users/${r.userId}/reject`), `${r.loginId} 가입 신청을 거절했습니다.`);
        }} onCancel={() => setReject(null)} />
    </div>
  );
}

function FarmChecks({ farms, value, onChange }: { farms: { farmId: number; farmName: string }[]; value: number[]; onChange: (v: number[]) => void }) {
  return (
    <fieldset className="text-sm">
      <legend className="mb-1 font-medium text-slate-700">접근 농장</legend>
      {farms.map((f) => (
        <label key={f.farmId} className="mr-3 inline-flex items-center gap-1">
          <input type="checkbox" checked={value.includes(f.farmId)}
            onChange={() => onChange(value.includes(f.farmId) ? value.filter((x) => x !== f.farmId) : [...value, f.farmId])} />
          {f.farmName}
        </label>
      ))}
    </fieldset>
  );
}
