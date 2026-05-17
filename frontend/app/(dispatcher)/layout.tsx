/**
 * FILE: frontend/app/(dispatcher)/layout.tsx
 * PURPOSE: Route-group shell for the Keiracom Dispatcher Product Layer
 *          (Part 17). Separate from the existing (auth) + Agency_OS
 *          internal flows — dispatcher customers go through this group.
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

export default function DispatcherLayout({ children }: { children: ReactNode }) {
  return (
    <div data-route-group="dispatcher" className="min-h-screen">
      {children}
    </div>
  );
}
