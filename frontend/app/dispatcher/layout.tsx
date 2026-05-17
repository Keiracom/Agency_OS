/**
 * FILE: frontend/app/dispatcher/layout.tsx
 * PURPOSE: Path-prefixed shell for the Keiracom Dispatcher Product Layer
 *          (Part 17). URLs live under /dispatcher/* so they don't collide
 *          with the existing internal Agency_OS /signup + /dashboard
 *          routes — was previously a route group but Next.js parallel-route
 *          collision blocked the build.
 * KEI: 113 (parent scaffold) — sub-KEIs implement page logic:
 *          KEI-113A signup UI (KEI-154)
 *          KEI-113B BYO key entry (KEI-155)
 *          KEI-113C task submission (KEI-156)
 *          KEI-113D dashboard populate (KEI-157)
 *
 * Stub layout only — auth provider + theme + nav-shell land in
 * KEI-113A (signup UI implementation) and KEI-114 (dashboard).
 */

import type { ReactNode } from "react";

interface DispatcherLayoutProps {
  children: ReactNode;
}

export default function DispatcherLayout({ children }: Readonly<DispatcherLayoutProps>) {
  return (
    <div data-route-prefix="dispatcher" className="min-h-screen">
      {children}
    </div>
  );
}
