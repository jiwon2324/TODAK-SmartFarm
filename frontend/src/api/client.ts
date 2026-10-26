// API 클라이언트: Access Token은 메모리에만 두고(XSS로 localStorage 탈취 방지),
// 만료되면 HttpOnly 쿠키의 Refresh Token으로 한 번 갱신한 뒤 다시 요청한다.

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onLoggedOut: (() => void) | null = null;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

export function setAccessToken(t: string | null) {
  accessToken = t;
}

export function getAccessToken() {
  return accessToken;
}

export function setLoggedOutHandler(fn: () => void) {
  onLoggedOut = fn;
}

export async function refreshToken(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch('/api/auth/refresh', { method: 'POST', credentials: 'include', headers: { 'X-TODAK-CSRF': '1' } })
      .then(async (r) => {
        if (!r.ok) return false;
        const body = await r.json();
        accessToken = body.accessToken;
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

async function raw(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const res = await fetch(path, { ...init, headers, credentials: 'include' });
  if (res.status === 401 && retry && !path.startsWith('/api/auth/')) {
    if (await refreshToken()) return raw(path, init, false);
    accessToken = null;
    onLoggedOut?.();
  }
  return res;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await raw(path, init);
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new ApiError(res.status, body?.code ?? 'ERROR', body?.message ?? `요청 실패 (${res.status})`);
  }
  return body as T;
}

export const get = <T,>(p: string) => api<T>(p);
export const post = <T,>(p: string, body?: unknown, headers?: Record<string, string>) =>
  api<T>(p, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body ?? {}), headers });
export const patch = <T,>(p: string, body: unknown) => api<T>(p, { method: 'PATCH', body: JSON.stringify(body) });
export const put = <T,>(p: string, body: unknown) => api<T>(p, { method: 'PUT', body: JSON.stringify(body) });
export const del = <T,>(p: string) => api<T>(p, { method: 'DELETE' });

/** 인증이 필요한 파일 다운로드 (CSV) */
export async function download(path: string, fileName: string) {
  const res = await raw(path);
  if (!res.ok) throw new ApiError(res.status, 'DOWNLOAD_FAILED', '다운로드 실패');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}

export function newIdempotencyKey() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}
