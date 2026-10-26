import { ReactNode, useState } from 'react';

export function Card({ title, action, children, className = '' }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}>
      {(title || action) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title && <h2 className="text-base font-semibold text-slate-800">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

const TONES = {
  green: 'bg-leaf-50 text-leaf-700 ring-leaf-100',
  red: 'bg-red-50 text-red-700 ring-red-100',
  amber: 'bg-amber-50 text-amber-800 ring-amber-100',
  blue: 'bg-sky-50 text-sky-800 ring-sky-100',
  gray: 'bg-slate-100 text-slate-600 ring-slate-200',
  violet: 'bg-violet-50 text-violet-700 ring-violet-100',
};

export function Badge({ tone = 'gray', children }: { tone?: keyof typeof TONES; children: ReactNode }) {
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${TONES[tone]}`}>{children}</span>;
}

export function Button({
  children, onClick, variant = 'primary', disabled, type = 'button', small, full, title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  disabled?: boolean;
  type?: 'button' | 'submit';
  small?: boolean;
  full?: boolean;
  title?: string;
}) {
  const v = {
    primary: 'bg-leaf-500 text-white hover:bg-leaf-600',
    secondary: 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    ghost: 'text-leaf-700 hover:bg-leaf-50',
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title}
      className={`${small ? 'px-2.5 py-1 text-sm' : 'px-4 py-2.5 text-sm'} ${full ? 'w-full' : ''} whitespace-nowrap rounded-lg font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-leaf-500 disabled:cursor-not-allowed disabled:opacity-50 ${v}`}>
      {children}
    </button>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: 'red' | 'amber' }) {
  const c = tone === 'red' ? 'text-red-600' : tone === 'amber' ? 'text-amber-700' : 'text-slate-900';
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${c}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export function PageTitle({ title, desc, action }: { title: string; desc?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{title}</h1>
        {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
      </div>
      {action}
    </div>
  );
}

export function SimNotice() {
  return (
    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
      표시되는 센서값은 <b>가상 센서 시뮬레이터(B안)</b>가 만든 시뮬레이션 데이터입니다. 실제 양평 기상 관측값이나 농가 실측값이 아닙니다.
    </div>
  );
}

export function ErrorBox({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{msg}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-8 text-center text-sm text-slate-500">{children}</div>;
}

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="-mx-4 overflow-x-auto px-4">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs text-slate-500">
            {head.map((h, i) => (
              <th key={i} className="whitespace-nowrap py-2 pr-3 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}

export function ConfirmDialog({
  open, title, body, confirmLabel = '실행', danger, onConfirm, onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl">
        <h3 className="text-lg font-semibold">{title}</h3>
        <div className="mt-2 text-sm text-slate-600">{body}</div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>취소</Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}

export const inputCls = 'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-leaf-500 focus:outline-none focus:ring-2 focus:ring-leaf-100';

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-slate-600">{label}</span>
      {children}
    </label>
  );
}

const NOTICE = {
  info: 'border-sky-200 bg-sky-50 text-sky-900',
  ok: 'border-leaf-100 bg-leaf-50 text-leaf-700',
  warn: 'border-amber-200 bg-amber-50 text-amber-900',
  error: 'border-red-200 bg-red-50 text-red-800',
};

export function Notice({ tone = 'info', children, className = '' }: { tone?: keyof typeof NOTICE; children: ReactNode; className?: string }) {
  if (!children) return null;
  return <div role={tone === 'error' ? 'alert' : 'status'} className={`mb-3 rounded-lg border px-3 py-2 text-sm ${NOTICE[tone]} ${className}`}>{children}</div>;
}

export function Modal({ open, title, children, onClose, wide }: { open: boolean; title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label={title}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}>
      <div className={`max-h-[90vh] w-full overflow-y-auto rounded-xl bg-white p-5 shadow-xl ${wide ? 'max-w-2xl' : 'max-w-md'}`}>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} aria-label="닫기" className="rounded p-1 text-slate-500 hover:bg-slate-100">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** 오류 메시지·도움말을 함께 보여 주는 입력 필드 (KWCAG: label·aria-describedby 연결) */
export function FormField({ id, label, required, hint, error, ok, children }: {
  id: string; label: string; required?: boolean; hint?: ReactNode; error?: string | null; ok?: string | null; children: ReactNode;
}) {
  return (
    <div className="text-sm">
      <label htmlFor={id} className="mb-1 block font-medium text-slate-700">
        {label}{required && <span className="ml-0.5 text-red-600" aria-label="필수">*</span>}
      </label>
      {children}
      {error ? <p id={`${id}-msg`} className="mt-1 text-xs text-red-700">{error}</p>
        : ok ? <p id={`${id}-msg`} className="mt-1 text-xs text-leaf-700">{ok}</p>
          : hint ? <p id={`${id}-msg`} className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function PasswordInput({ id, value, onChange, autoComplete, placeholder, invalid, onBlur }: {
  id: string; value: string; onChange: (v: string) => void; autoComplete: string; placeholder?: string; invalid?: boolean; onBlur?: () => void;
}) {
  const [show, setShow] = useState(false);
  const [caps, setCaps] = useState(false);
  return (
    <div>
      <div className="relative">
        <input id={id} type={show ? 'text' : 'password'} value={value} autoComplete={autoComplete} placeholder={placeholder}
          aria-invalid={invalid || undefined} aria-describedby={`${id}-msg`} onBlur={onBlur}
          onChange={(e) => onChange(e.target.value)}
          onKeyUp={(e) => setCaps(e.getModifierState('CapsLock'))} onKeyDown={(e) => setCaps(e.getModifierState('CapsLock'))}
          className={`${inputCls} pr-16 ${invalid ? 'border-red-400' : ''}`} />
        <button type="button" onClick={() => setShow(!show)} aria-pressed={show}
          className="absolute inset-y-0 right-1 my-1 rounded-md px-2 text-xs text-slate-600 hover:bg-slate-100">{show ? '숨기기' : '보기'}</button>
      </div>
      {caps && <p className="mt-1 text-xs text-amber-800">Caps Lock이 켜져 있습니다</p>}
    </div>
  );
}

export function Spinner() {
  return <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white align-[-2px]" aria-hidden="true" />;
}
