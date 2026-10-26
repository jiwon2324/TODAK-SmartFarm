import { FormEvent, useCallback, useEffect, useState } from 'react';
import { get, patch, post, put } from '../../api/client';
import type { AdminUser } from '../../api/types';
import { fmtTime } from '../../components/format';
import { useFarm } from '../../components/Layout';
import { Badge, Button, Card, ErrorBox, Field, PageTitle, Table, inputCls } from '../../components/ui';

/** SCR-A2 사용자 관리: 등록·수정·활성/비활성·역할·농장 접근 권한·비밀번호 초기화 [REQ-F-12] */
export default function Users() {
  const { farms } = useFarm();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [form, setForm] = useState({ loginId: '', password: '', name: '', phone: '', role: 'FARMER', farmIds: [] as number[] });

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
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const create = (e: FormEvent) => {
    e.preventDefault();
    act(() => post('/api/admin/users', form), `${form.loginId} 사용자를 등록했습니다.`).then(() =>
      setForm({ loginId: '', password: '', name: '', phone: '', role: 'FARMER', farmIds: [] }));
  };

  const toggleFarm = (u: AdminUser, f: number) => {
    const next = u.farmIds.includes(f) ? u.farmIds.filter((x) => x !== f) : [...u.farmIds, f];
    act(() => put(`/api/admin/users/${u.userId}/farms`, next), `${u.loginId}의 농장 권한을 바꿨습니다.`);
  };

  const resetPw = (u: AdminUser) => {
    const pw = window.prompt(`${u.loginId}의 새 비밀번호 (8자 이상)`);
    if (pw) act(() => patch(`/api/admin/users/${u.userId}`, { newPassword: pw }), '비밀번호를 바꾸고 기존 로그인 세션을 모두 폐기했습니다.');
  };

  return (
    <div>
      <PageTitle title="사용자 관리" desc="농가 사용자는 체크한 농장의 데이터만 볼 수 있습니다. 비활성화하면 즉시 모든 세션이 끊깁니다." />
      <ErrorBox msg={err} />
      {msg && <div className="mb-3 rounded-lg border border-leaf-100 bg-leaf-50 px-3 py-2 text-sm text-leaf-700">{msg}</div>}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="사용자 목록" className="xl:col-span-2">
          <Table head={['아이디', '이름', '역할', '상태', '농장 권한', '가입', '']}>
            {users.map((u) => (
              <tr key={u.userId}>
                <td className="py-2 pr-3 font-medium">{u.loginId}</td>
                <td className="pr-3">{u.name}</td>
                <td className="pr-3">
                  <select className="rounded border border-slate-300 px-1 py-0.5" value={u.role}
                    onChange={(e) => act(() => patch(`/api/admin/users/${u.userId}`, { role: e.target.value }), '역할을 바꿨습니다.')}>
                    <option value="FARMER">농가</option><option value="ADMIN">관리자</option>
                  </select>
                </td>
                <td className="pr-3">
                  <Badge tone={u.isActive ? 'green' : 'gray'}>{u.isActive ? '활성' : '비활성'}</Badge>
                  {u.lockedUntil && new Date(u.lockedUntil) > new Date() && <Badge tone="red">잠금</Badge>}
                </td>
                <td className="pr-3">
                  {u.role === 'ADMIN' ? <span className="text-xs text-slate-400">전체</span> : farms.map((f) => (
                    <label key={f.farmId} className="mr-2 inline-flex items-center gap-1 text-xs">
                      <input type="checkbox" checked={u.farmIds.includes(f.farmId)} onChange={() => toggleFarm(u, f.farmId)} />{f.farmName}
                    </label>
                  ))}
                </td>
                <td className="whitespace-nowrap pr-3 text-xs">{fmtTime(u.createdAt)}</td>
                <td className="whitespace-nowrap">
                  <Button small variant="ghost" onClick={() => act(() => patch(`/api/admin/users/${u.userId}`, { isActive: !u.isActive }), u.isActive ? '비활성화했습니다.' : '활성화했습니다.')}>
                    {u.isActive ? '비활성화' : '활성화'}
                  </Button>
                  <Button small variant="ghost" onClick={() => resetPw(u)}>비밀번호</Button>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
        <Card title="사용자 등록">
          <form onSubmit={create} className="space-y-3">
            <Field label="아이디 (영문·숫자 4자 이상)"><input className={inputCls} value={form.loginId} onChange={(e) => setForm({ ...form, loginId: e.target.value })} required /></Field>
            <Field label="비밀번호 (8자 이상)"><input type="password" className={inputCls} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} /></Field>
            <Field label="이름"><input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
            <Field label="연락처"><input className={inputCls} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="역할">
              <select className={inputCls} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="FARMER">농가</option><option value="ADMIN">관리자</option>
              </select>
            </Field>
            <div className="text-sm">
              <div className="mb-1 text-slate-600">농장 권한</div>
              {farms.map((f) => (
                <label key={f.farmId} className="mr-3 inline-flex items-center gap-1">
                  <input type="checkbox" checked={form.farmIds.includes(f.farmId)}
                    onChange={() => setForm({ ...form, farmIds: form.farmIds.includes(f.farmId) ? form.farmIds.filter((x) => x !== f.farmId) : [...form.farmIds, f.farmId] })} />
                  {f.farmName}
                </label>
              ))}
            </div>
            <Button type="submit">등록</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
