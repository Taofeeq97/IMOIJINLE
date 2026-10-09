"use client";

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";

import { api, setAccessToken } from "@/lib/api/client";
import type { UserMe } from "@/lib/api/schema";
import { loginRedirectUrl, registerSessionExpiredHandler } from "@/lib/auth/session";

type AuthContextValue = {
  user: UserMe | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserMe>;
  acceptSession: (access: string, user: UserMe) => void;
  logout: () => Promise<void>;
  refreshSession: () => Promise<UserMe | null>;
  hasPermission: (action: string) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshSession = useCallback(async () => {
    try {
      const refreshed = await api.refresh();
      setAccessToken(refreshed.access);
      setUser(refreshed.user);
      return refreshed.user;
    } catch {
      setAccessToken(null);
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    registerSessionExpiredHandler((reason) => {
      setAccessToken(null);
      setUser(null);
      toast.error(reason || "Session expired. Please sign in again.");
      if (typeof window !== "undefined") {
        window.location.assign(loginRedirectUrl());
      }
    });
    return () => registerSessionExpiredHandler(null);
  }, []);

  useEffect(() => {
    void (async () => {
      await refreshSession();
      setLoading(false);
    })();
  }, [refreshSession]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    setAccessToken(res.access);
    setUser(res.user);
    return res.user;
  }, []);

  const acceptSession = useCallback((access: string, nextUser: UserMe) => {
    setAccessToken(access);
    setUser(nextUser);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const hasPermission = useCallback(
    (action: string) => Boolean(user?.permissions.includes(action)),
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, acceptSession, logout, refreshSession, hasPermission }),
    [user, loading, login, acceptSession, logout, refreshSession, hasPermission],
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function Can({
  action,
  children,
  fallback = null,
}: {
  action: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasPermission } = useAuth();
  if (!hasPermission(action)) return <>{fallback}</>;
  return <>{children}</>;
}
