"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import type { RoleCode } from "@aureon/shared-types";
import { loginApi, switchRoleApi } from "./auth-api";
import type { AuthSession, AuthUser } from "./types";

const AUTH_STORAGE_KEY = "aureon_demo_auth_session";

export interface AuthContextValue {
  session: AuthSession | null;
  user: AuthUser | null;
  role: RoleCode;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthSession>;
  switchRole: (targetRoleCode: RoleCode) => Promise<AuthSession>;
  logout: () => void;
  setSession: (session: AuthSession | null) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({
  children,
  initialSession,
}: {
  children: ReactNode;
  initialSession?: AuthSession | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [session, setSessionState] = useState<AuthSession | null>(initialSession ?? null);
  const [isLoading, setIsLoading] = useState<boolean>(!initialSession);

  // Restore session from localStorage on mount
  useEffect(() => {
    if (initialSession !== undefined) {
      setIsLoading(false);
      return;
    }
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as AuthSession;
        if (parsed && parsed.accessToken && parsed.user) {
          setSessionState(parsed);
        }
      }
    } catch {
      // Ignore storage errors in restricted contexts
    } finally {
      setIsLoading(false);
    }
  }, [initialSession]);

  const setSession = useCallback((newSession: AuthSession | null) => {
    setSessionState(newSession);
    try {
      if (newSession) {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(newSession));
      } else {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    } catch {
      // Storage access blocked or quota exceeded
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string): Promise<AuthSession> => {
      const data = await loginApi(email, password);
      const newSession: AuthSession = {
        accessToken: data.access_token,
        user: data.user,
        expiresAt: data.expires_at,
        homeRoute: data.user.role.home_route,
      };
      setSession(newSession);
      router.push(newSession.homeRoute);
      return newSession;
    },
    [router, setSession],
  );

  const switchRole = useCallback(
    async (targetRoleCode: RoleCode): Promise<AuthSession> => {
      const startMs = performance.now();
      if (!session) {
        throw new Error("No active session to switch role from");
      }
      const data = await switchRoleApi(targetRoleCode, session.accessToken);
      const newSession: AuthSession = {
        accessToken: data.access_token,
        user: data.user,
        expiresAt: data.expires_at,
        homeRoute: data.home_route,
      };

      // 02 §5.2 R3 & 07 §8.1.1: Purge TanStack Query client cache
      queryClient.clear();

      setSession(newSession);

      // 02 §5.2 R1 / TC-KPI-002: Log KPI duration
      const elapsedMs = performance.now() - startMs;
      if (process.env.NODE_ENV !== "production") {
        console.info(`[KPI-002] Role switched to ${targetRoleCode} in ${elapsedMs.toFixed(1)}ms`);
      }

      router.push(newSession.homeRoute);
      return newSession;
    },
    [queryClient, router, session, setSession],
  );

  const logout = useCallback(() => {
    setSession(null);
    queryClient.clear();
    router.push("/login");
  }, [queryClient, router, setSession]);

  const role: RoleCode = session?.user?.role?.code ?? "ROLE-01";
  const user: AuthUser | null = session?.user ?? null;
  const isAuthenticated = !!session?.accessToken;

  return (
    <AuthContext.Provider
      value={{
        session,
        user,
        role,
        isAuthenticated,
        isLoading,
        login,
        switchRole,
        logout,
        setSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthSafe(): AuthContextValue | null {
  return useContext(AuthContext);
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
