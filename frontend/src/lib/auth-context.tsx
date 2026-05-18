"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { loginUser, signupUser } from "./api";

interface AuthUser { user_id: string; email: string; access_token: string }

interface AuthCtx {
  user: AuthUser | null;
  authLoading: boolean;
  login:  (email: string, password: string) => Promise<string | null>;
  signup: (email: string, password: string) => Promise<{ error: string | null; needsConfirm?: boolean }>;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx | null>(null);

const STORAGE_KEY = "pakflood_auth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw) as AuthUser);
    } catch {
      // ignore malformed storage
    }
    setAuthLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<string | null> => {
    try {
      const res = await loginUser(email, password);
      const u: AuthUser = { user_id: res.user_id, email: res.email, access_token: res.access_token };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
      setUser(u);
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : "Login failed";
    }
  };

  const signup = async (email: string, password: string) => {
    try {
      const res = await signupUser(email, password);
      if (res.access_token && res.user_id && res.email) {
        const u: AuthUser = { user_id: res.user_id, email: res.email, access_token: res.access_token };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
        setUser(u);
        return { error: null };
      }
      // Email confirmation required
      return { error: null, needsConfirm: true };
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Signup failed" };
    }
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, authLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
