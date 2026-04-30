/**
 * FILE: frontend/components/dashboard/SystemHealth.tsx
 * PURPOSE: System Health surface — A3 dispatch (2026-04-30) replaced
 *          the prior mocked 4-pill grid with an honest "Coming soon"
 *          empty state. The backend has the raw signals (Resend
 *          delivery, LinkedIn queue depth, VAPI status, Telnyx) but
 *          no aggregated /api/v1/system-health endpoint yet, so
 *          fabricating green/amber/red pills here would mislead
 *          investors viewing the demo.
 *
 * Component name preserved for backwards-compat with existing imports.
 * Becomes a real live health grid once the aggregator endpoint exists.
 */

"use client";

import { Activity } from "lucide-react";
import { TodoMockPanel } from "./TodoMockPanel";

export function SystemHealth() {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold">
          System Health
        </div>
      </div>

      <TodoMockPanel
        icon={<Activity className="w-4 h-4" strokeWidth={1.6} />}
        eyebrow="Channel uptime"
        title="Channel health coming soon"
        description="Email, LinkedIn, voice, and SMS provider status will appear here as a single live grid once the aggregator endpoint ships."
      />
    </section>
  );
}
