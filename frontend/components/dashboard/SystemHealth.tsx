/**
 * FILE: frontend/components/dashboard/SystemHealth.tsx
 * PURPOSE: 4 channel health pills — Email Delivery / LinkedIn Queue /
 *          Voice AI / SMS Gateway. Green/amber/red status dots.
 *          PR2 dashboard rebuild.
 * REFERENCE: dashboard-master-agency-desk.html — `.tb-cycle .tb-dot`
 *            (pulsing dot) + `.pill` colour scheme.
 */

"use client";

import { Mail, Linkedin, Phone, MessageSquare, type LucideIcon } from "lucide-react";

type HealthStatus = "ok" | "warn" | "error";

interface ChannelHealth {
  id: string;
  label: string;
  icon: LucideIcon;
  status: HealthStatus;
  detail: string;     // short subtitle, e.g. "98.2% delivered"
}

const STATUS_COLOR: Record<HealthStatus, { bg: string; ring: string; text: string }> = {
  ok:    { bg: "var(--green)", ring: "rgba(107,142,90,0.35)", text: "var(--green)" },
  warn:  { bg: "var(--amber)", ring: "rgba(212,149,106,0.35)", text: "var(--copper)" },
  error: { bg: "var(--red)",   ring: "rgba(181,90,76,0.35)",   text: "var(--red)" },
};

/**
 * TODO(api): SystemHealth is currently mock-only. The backend has the
 * raw signals needed (`distribution.email`, LinkedIn queue depth, voice
 * provider status, telnyx SMS gateway) but no aggregated /api/v1/system-
 * health endpoint exists yet. Each card below carries a `todo` flag so a
 * follow-up PR can wire `useSystemHealth()` without changing the layout.
 */
function useSystemHealthMock(): ChannelHealth[] {
  return [
    {
      id: "email",
      label: "Email Delivery",
      icon: Mail,
      status: "ok",
      detail: "98.2% delivered · last 24h",
    },
    {
      id: "linkedin",
      label: "LinkedIn Queue",
      icon: Linkedin,
      status: "warn",
      detail: "Weekend slowdown · 12 queued",
    },
    {
      id: "voice",
      label: "Voice AI",
      icon: Phone,
      status: "ok",
      detail: "VAPI healthy · 0 failures",
    },
    {
      id: "sms",
      label: "SMS Gateway",
      icon: MessageSquare,
      status: "ok",
      detail: "Telnyx · 100% uptime",
    },
  ];
}

export function SystemHealth() {
  const channels = useSystemHealthMock();

  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold">
          System Health
        </div>
        <span className="font-mono text-[8px] tracking-[0.12em] uppercase text-amber/80 bg-amber-soft border border-amber/30 rounded px-1.5 py-[1px]">
          TODO · MOCK
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {channels.map(channel => (
          <HealthPill key={channel.id} channel={channel} />
        ))}
      </div>
    </section>
  );
}

function HealthPill({ channel }: { channel: ChannelHealth }) {
  const Icon = channel.icon;
  const palette = STATUS_COLOR[channel.status];
  const labelText = {
    ok: "Operational",
    warn: "Degraded",
    error: "Outage",
  }[channel.status];

  return (
    <div className="rounded-[10px] border border-rule bg-panel px-4 py-3.5 flex items-start gap-3">
      <Icon className="w-4 h-4 mt-0.5 text-ink-3 shrink-0" strokeWidth={1.6} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {/* Status dot */}
          <span className="relative flex w-2 h-2">
            {channel.status === "ok" && (
              <span
                className="absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping"
                style={{ backgroundColor: palette.bg }}
              />
            )}
            <span
              className="relative inline-flex w-2 h-2 rounded-full"
              style={{ backgroundColor: palette.bg, boxShadow: `0 0 0 3px ${palette.ring}` }}
            />
          </span>

          <span className="font-mono text-[10px] tracking-[0.1em] uppercase font-semibold" style={{ color: palette.text }}>
            {labelText}
          </span>
        </div>

        <div className="text-[13px] text-ink mt-1.5 font-medium truncate">
          {channel.label}
        </div>
        <div className="text-[11.5px] text-ink-3 mt-0.5 truncate">
          {channel.detail}
        </div>
      </div>
    </div>
  );
}
