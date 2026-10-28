// 스냅샷 데모 모드 (VITE_SNAPSHOT=1 빌드에서만 켜짐)
// 서버 없이 GitHub Pages에서 열리도록, 실제 시스템에서 기록한 GET 응답(tools/snapshot/record.py)을 돌려준다.
// 기록 시각에 시계를 맞추고, 장치 제어·설정 변경 같은 쓰기 요청은 막는다.

export const SNAPSHOT = import.meta.env.VITE_SNAPSHOT === '1';
export let snapshotAt = '';

const DROP = new Set(['from', 'to', 'size']);

function normalize(url: URL) {
  const q = [...url.searchParams].filter(([k]) => !DROP.has(k)).sort(([a, av], [b, bv]) => (a === b ? av.localeCompare(bv) : a.localeCompare(b)));
  return url.pathname + (q.length ? '?' + new URLSearchParams(q).toString() : '');
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** 기록한 넓은 범위의 응답을 요청한 기간·개수만큼 잘라 준다 */
function trim(body: unknown, url: URL) {
  const from = url.searchParams.get('from');
  const to = url.searchParams.get('to');
  const size = Number(url.searchParams.get('size') ?? 0);
  const inRange = (t?: string) => !t || ((!from || t >= from) && (!to || t <= to + (to.length === 10 ? 'T99' : '')));
  if (Array.isArray(body)) {
    let rows = body.filter((r) => inRange((r as { date?: string }).date));
    if (size) rows = rows.slice(0, size);
    return rows;
  }
  if (body && typeof body === 'object' && Array.isArray((body as { points?: unknown[] }).points)) {
    const b = body as { points: { t: string }[] };
    return { ...b, points: b.points.filter((p) => inRange(p.t)) };
  }
  return body;
}

export async function startSnapshot() {
  const base = import.meta.env.BASE_URL;
  const realFetch = window.fetch.bind(window);
  const index: { capturedAt: string; files: Record<string, string> } = await realFetch(`${base}snapshot/index.json`).then((r) => r.json());
  snapshotAt = index.capturedAt;

  // 시계를 기록 시각으로 (지난 시간만큼은 흐르게)
  const RealDate = Date;
  const offset = new RealDate(index.capturedAt).getTime() - RealDate.now();
  class SnapDate extends RealDate {
    constructor(...a: unknown[]) {
      if (a.length === 0) super(RealDate.now() + offset);
      else super(...(a as [string]));
    }
    static now() {
      return RealDate.now() + offset;
    }
  }
  window.Date = SnapDate as DateConstructor;

  const cache = new Map<string, Promise<unknown>>();
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, location.origin);
    if (!url.pathname.startsWith('/api/')) return realFetch(input, init);
    const method = (init?.method ?? 'GET').toUpperCase();
    if (['/api/auth/refresh', '/api/auth/login', '/api/auth/demo'].includes(url.pathname) && method === 'POST') return json({ accessToken: 'snapshot' });
    if (url.pathname === '/api/auth/logout') return json({});
    if (url.pathname === '/api/auth/demo') return json({ enabled: true });
    if (method !== 'GET') return json({ code: 'SNAPSHOT', message: '스냅샷 데모에서는 장치 제어·설정 변경을 할 수 없습니다 (화면 둘러보기 전용).' }, 403);
    const file = index.files[normalize(url)];
    if (!file) return json({ code: 'SNAPSHOT', message: '스냅샷 데모에 기록되지 않은 데이터입니다.' }, 404);
    if (!cache.has(file)) cache.set(file, realFetch(`${base}snapshot/${file}`).then((r) => r.json()));
    return json(trim(await cache.get(file), url));
  };

  // 실시간 스트림(SSE)은 연결된 것처럼만 보이게
  class SnapEventSource extends EventTarget {
    onopen: ((e: Event) => void) | null = null;
    onerror: ((e: Event) => void) | null = null;
    readyState = 1;
    constructor() {
      super();
      setTimeout(() => this.onopen?.(new Event('open')), 0);
    }
    close() {
      this.readyState = 2;
    }
  }
  window.EventSource = SnapEventSource as unknown as typeof EventSource;
}
