import { createContext, useCallback, useMemo, useState, type ReactNode } from 'react';
import * as authApi from '../api/auth';
import { clearStoredToken, getStoredToken, getStoredUser, setStoredToken, setStoredUser } from '../api/client';
import type { UserRead } from '../types/user';

export interface AuthContextValue {
  user: UserRead | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(() => getStoredUser<UserRead>());
  const [token, setToken] = useState<string | null>(() => getStoredToken());

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password });
    setStoredToken(res.access_token);
    setStoredUser(res.user);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    authApi.logout().catch(() => {
      /* client-side discard regardless of network result */
    });
    clearStoredToken();
    setToken(null);
    setUser(null);
  }, []);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  // Expose a way for the query client's global error handler to clear session on 401.
  useMemo(() => {
    (window as unknown as { __authClearSession?: () => void }).__authClearSession = clearSession;
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token && user),
      isLoading: false,
      login,
      logout,
    }),
    [user, token, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
