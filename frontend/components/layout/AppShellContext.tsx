/**
 * FILE: frontend/components/layout/AppShellContext.tsx
 * PURPOSE: Carries server-fetched user + client context down to the
 *          AppShell client component without each sub-route having
 *          to thread props through.
 *
 *          Used by `app/dashboard/layout.tsx` (server) — it loads
 *          the auth user + active client server-side, wraps children
 *          in this provider, and the AppShell each sub-route renders
 *          calls `useAppShellContext()` to populate the Sidebar
 *          footer + Header pause-all button + credits badge.
 *
 *          When the provider isn't present (e.g. AppShell rendered
 *          from a marketing page), the hook returns an empty object
 *          and AppShell falls back to its anonymous defaults.
 */

"use client";

import { createContext, useContext, type ReactNode } from "react";

export interface AppShellUser {
  email: string;
  fullName?: string;
  avatarUrl?: string;
}

export interface AppShellClient {
  id: string;
  name: string;
  tier: string;
  creditsRemaining: number;
  pausedAt?: string | null;
  pauseReason?: string | null;
}

export interface AppShellContextValue {
  user?: AppShellUser;
  client?: AppShellClient;
}

const AppShellCtx = createContext<AppShellContextValue>({});

export function AppShellProvider({
  user, client, children,
}: AppShellContextValue & { children: ReactNode }) {
  return (
    <AppShellCtx.Provider value={{ user, client }}>
      {children}
    </AppShellCtx.Provider>
  );
}

export function useAppShellContext(): AppShellContextValue {
  return useContext(AppShellCtx);
}
