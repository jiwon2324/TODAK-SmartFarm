import { useCallback, useEffect, useRef, useState } from 'react';
import { get, getAccessToken } from '../api/client';

/** GET 요청 상태 관리. deps가 바뀌면 다시 불러오고, reload()로 수동 갱신 */
export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try {
      setData(await get<T>(path));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => {
    load();
  }, [load]);
  return { data, error, loading, reload: load, setData };
}

export type StreamEvent = { type: 'reading' | 'device' | 'command' | 'alert'; data: Record<string, unknown> };

/** 농장 SSE 구독 (/api/stream). 끊기면 브라우저가 자동 재연결, 토큰 만료 시 15초 뒤 새 토큰으로 다시 연결 */
export function useFarmStream(farmId: number | null, onEvent: (e: StreamEvent) => void) {
  const handler = useRef(onEvent);
  handler.current = onEvent;
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!farmId) return;
    let es: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const open = () => {
      const token = getAccessToken();
      if (!token) return;
      es = new EventSource(`/api/stream?farmId=${farmId}&access_token=${encodeURIComponent(token)}`);
      es.onopen = () => setConnected(true);
      es.onerror = () => {
        setConnected(false);
        es?.close();
        timer = setTimeout(open, 15000);
      };
      for (const type of ['reading', 'device', 'command', 'alert'] as const) {
        es.addEventListener(type, (m) => handler.current({ type, data: JSON.parse((m as MessageEvent).data) }));
      }
    };
    open();
    return () => {
      es?.close();
      if (timer) clearTimeout(timer);
    };
  }, [farmId]);
  return connected;
}
