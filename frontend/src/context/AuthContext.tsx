/**
 * AuthContext — keeps the current student in React state, persists tokens
 * to localStorage on login, restores the session on page load.
 *
 * The app's existing top-level switch (App.tsx) uses `isAuthenticated`
 * for navigation; pages that need profile data can call `useAuth()`.
 */
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api, tokenStore, Student } from '../lib/api';

interface AuthContextValue {
  student: Student | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    fullName: string;
    formLevel: number;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<Student | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  // On mount: if we have a stored access token, try to fetch /me to
  // restore the session.
  useEffect(() => {
    (async () => {
      if (!tokenStore.getAccess()) {
        setIsInitializing(false);
        return;
      }
      try {
        const me = await api.getMe();
        setStudent(me);
      } catch {
        tokenStore.clear();
      } finally {
        setIsInitializing(false);
      }
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.login({ email, password });
    tokenStore.set(res.accessToken, res.refreshToken);
    setStudent(res.student);
  };

  const register = async (payload: {
    email: string;
    password: string;
    fullName: string;
    formLevel: number;
  }) => {
    const res = await api.register(payload);
    tokenStore.set(res.accessToken, res.refreshToken);
    setStudent(res.student);
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      /* even if the call fails, clear local state */
    }
    tokenStore.clear();
    setStudent(null);
  };

  const refreshProfile = async () => {
    try {
      const me = await api.getMe();
      setStudent(me);
    } catch {
      /* ignore */
    }
  };

  return (
    <AuthContext.Provider
      value={{
        student,
        isAuthenticated: !!student,
        isInitializing,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside an AuthProvider');
  return ctx;
}
