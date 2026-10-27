import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { get, post, refreshToken, setAccessToken, setLoggedOutHandler } from '../api/client';
import type { Me } from '../api/types';

interface AuthState {
  me: Me | null;
  loading: boolean;
  /** 세션이 만료돼 로그인 화면으로 돌아왔을 때 안내 문구 */
  expired: boolean;
  login: (loginId: string, password: string) => Promise<Me>;
  /** 로그인 없이 둘러보기 (조회 전용 계정) */
  demo: () => Promise<Me>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
  /** 비밀번호 변경 등으로 새 Access Token을 받았을 때 */
  adoptToken: (token: string) => Promise<void>;
}

const Ctx = createContext<AuthState>(null as unknown as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    setLoggedOutHandler(() => {
      setMe((prev) => {
        if (prev) setExpired(true);
        return null;
      });
    });
    // 새로고침: HttpOnly 쿠키로 Access Token을 다시 받아 세션 복원
    refreshToken()
      .then(async (ok) => (ok ? setMe(await get<Me>('/api/auth/me')) : setMe(null)))
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  const reload = useCallback(async () => {
    setMe(await get<Me>('/api/auth/me'));
  }, []);

  const login = useCallback(async (loginId: string, password: string) => {
    const r = await post<{ accessToken: string }>('/api/auth/login', { loginId, password });
    setAccessToken(r.accessToken);
    const m = await get<Me>('/api/auth/me');
    setExpired(false);
    setMe(m);
    return m;
  }, []);

  const demo = useCallback(async () => {
    const r = await post<{ accessToken: string }>('/api/auth/demo');
    setAccessToken(r.accessToken);
    const m = await get<Me>('/api/auth/me');
    setExpired(false);
    setMe(m);
    return m;
  }, []);

  const adoptToken = useCallback(async (token: string) => {
    setAccessToken(token);
    setMe(await get<Me>('/api/auth/me'));
  }, []);

  const logout = useCallback(async () => {
    try {
      await post('/api/auth/logout', {}, { 'X-TODAK-CSRF': '1' });
    } finally {
      setAccessToken(null);
      setExpired(false);
      setMe(null);
    }
  }, []);

  return <Ctx.Provider value={{ me, loading, expired, login, demo, logout, reload, adoptToken }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

/** 조회 전용(VIEWER) 계정이면 true — 버튼을 막는 것은 안내용이고 서버도 403으로 막는다 */
export const useReadOnly = () => useAuth().me?.role === 'VIEWER';

export const homeOf = (me: Me) => (me.mustChangePassword ? '/account/password' : me.role === 'ADMIN' ? '/admin' : '/farm');
