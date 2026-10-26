import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { get, post, refreshToken, setAccessToken, setLoggedOutHandler } from '../api/client';
import type { Me } from '../api/types';

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (loginId: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthState>(null as unknown as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoggedOutHandler(() => setMe(null));
    // 새로고침: HttpOnly 쿠키로 Access Token을 다시 받아 세션 복원
    refreshToken()
      .then(async (ok) => (ok ? setMe(await get<Me>('/api/auth/me')) : setMe(null)))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (loginId: string, password: string) => {
    const r = await post<{ accessToken: string }>('/api/auth/login', { loginId, password });
    setAccessToken(r.accessToken);
    const m = await get<Me>('/api/auth/me');
    setMe(m);
    return m;
  }, []);

  const logout = useCallback(async () => {
    try {
      await post('/api/auth/logout', {}, { 'X-TODAK-CSRF': '1' });
    } finally {
      setAccessToken(null);
      setMe(null);
    }
  }, []);

  return <Ctx.Provider value={{ me, loading, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
