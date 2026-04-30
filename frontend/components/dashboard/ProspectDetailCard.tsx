/**
 * FILE: frontend/components/dashboard/ProspectDetailCard.tsx
 * PURPOSE: Inline prospect briefing card — vulnerability text, A-F grade
 *          strip (website / SEO / reviews / ads / social / content),
 *          signal timeline (email/LinkedIn/voice/replies with quotes),
 *          meeting info with booking countdown. PR3 dashboard rebuild.
 *
 * REFERENCE: dashboard-master-agency-desk.html — `.bf-section`,
 *            `.vr-strip` / `.vr-letter`, `.event-card` / `.event-quote`,
 *            drawer body builder at line ~1300.
 *
 * The existing ProspectDrawer renders inside a slide-over panel. This
 * card is the inline equivalent for embedding directly in a page or
 * within the drawer body — both surfaces share styling (per prototype's
 * comment: "from drawer + briefing page so both surfaces stay
 * consistent").
 */

"use client";

import { useMemo } from "react";
import {
  Mail, Linkedin, Phone, MessageSquare, MessageSquareReply, Calendar,
  type LucideIcon,
} from "lucide-react";

export type Grade = "A" | "B" | "C" | "D" | "F";

export interface ProspectGrades {
  website?: Grade;
  seo?:     Grade;
  reviews?: Grade;
  ads?:     Grade;
  social?:  Grade;
  content?: Grade;
}

export type SignalKind =
  | "email_sent" | "email_opened" | "email_replied"
  | "linkedin_view" | "linkedin_invite" | "linkedin_message"
  | "voice_call" | "voice_voicemail"
  | "sms_sent" | "sms_replied"
  | "meeting_booked";

export interface ProspectSignal {
  id: string;
  kind: SignalKind;
  at: string;          // ISO timestamp
  headline: string;    // "Email opened — subject 'Quick question…'"
  quote?: string;      // optional reply quote rendered as Playfair italic
}

export interface ProspectMeeting {
  scheduledAt: string;   // ISO
  durationMin?: number;
  withName?: string;
  joinUrl?: string;
}

export interface ProspectDetail {
  id: string;
  name: string;
  company: string;
  vulnerability?: string;
  grades?: ProspectGrades;
  signals?: ProspectSignal[];
  meeting?: ProspectMeeting | null;
}

export function ProspectDetailCard({ prospect }: { prospect: ProspectDetail }) {
  return (
    <article className="rounded-[10px] border border-rule bg-panel p-5 sm:p-6 space-y-6">
      <Header prospect={prospect} />

      {prospect.vulnerability && (
        <Section label="Vulnerability analysis">
          <p className="text-[13px] text-ink-2 leading-relaxed">
            {prospect.vulnerability}
          </p>
          {prospect.grades && <GradeStrip grades={prospect.grades} />}
        </Section>
      )}

      {prospect.meeting && (
        <Section label="Meeting">
          <MeetingBlock meeting={prospect.meeting} />
        </Section>
      )}

      {prospect.signals && prospect.signals.length > 0 && (
        <Section label={`Signal timeline · ${prospect.signals.length} events`}>
          <Timeline signals={prospect.signals} />
        </Section>
      )}
    </article>
  );
}

// ─── Header ────────────────────────────────────────────────────────────────

function Header({ prospect }: { prospect: ProspectDetail }) {
  return (
    <div>
      <h2 className="font-display font-bold text-[24px] text-ink leading-tight">
        {prospect.company || prospect.name}
      </h2>
      {prospect.company && prospect.name && (
        <div className="font-mono text-[11px] tracking-[0.06em] text-ink-3 mt-1">
          {prospect.name}
        </div>
      )}
    </div>
  );
}

// ─── Section wrapper — matches .bf-section h4 ──────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section>
      <h4
        className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold pb-2 mb-3 border-b border-rule"
      >
        {label}
      </h4>
      {children}
    </section>
  );
}

// ─── A-F grade strip — matches .vr-strip / .vr-letter ──────────────────────

const GRADE_BG: Record<Grade, { bg: string; fg: string }> = {
  A: { bg: "var(--green)",  fg: "white" },
  B: { bg: "var(--green)",  fg: "white" },
  C: { bg: "var(--amber)",  fg: "var(--on-amber)" },
  D: { bg: "var(--copper)", fg: "white" },
  F: { bg: "var(--red)",    fg: "white" },
};

function GradeStrip({ grades }: { grades: ProspectGrades }) {
  const order: Array<keyof ProspectGrades> = [
    "website", "seo", "reviews", "ads", "social", "content",
  ];
  return (
    <div className="flex flex-wrap gap-3 mt-4">
      {order.map(k => {
        const g = grades[k];
        if (!g) return null;
        const palette = GRADE_BG[g];
        return (
          <div key={k} className="flex flex-col items-center gap-1.5">
            <div
              className="w-[34px] h-[34px] rounded-[6px] grid place-items-center font-display font-bold text-[15px]"
              style={{ backgroundColor: palette.bg, color: palette.fg }}
            >
              {g}
            </div>
            <span className="font-mono text-[10px] tracking-[0.06em] text-ink-3 capitalize">
              {k}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Timeline — matches .event-card / .event-quote ─────────────────────────

const SIGNAL_ICON: Record<SignalKind, {
  icon: LucideIcon;
  bg: string;
  color: string;
  type: string;
}> = {
  email_sent:      { icon: Mail,               bg: "rgba(12,10,8,0.05)",     color: "var(--ink-3)", type: "Email · Sent" },
  email_opened:    { icon: Mail,               bg: "var(--amber-soft)",      color: "var(--copper)", type: "Email · Opened" },
  email_replied:   { icon: MessageSquareReply, bg: "rgba(107,142,90,0.16)",  color: "var(--green)", type: "Email · Replied" },
  linkedin_view:   { icon: Linkedin,           bg: "rgba(74,111,165,0.14)",  color: "var(--blue)",  type: "LinkedIn · Profile view" },
  linkedin_invite: { icon: Linkedin,           bg: "rgba(74,111,165,0.14)",  color: "var(--blue)",  type: "LinkedIn · Invite sent" },
  linkedin_message:{ icon: Linkedin,           bg: "rgba(74,111,165,0.14)",  color: "var(--blue)",  type: "LinkedIn · Message" },
  voice_call:      { icon: Phone,              bg: "rgba(196,106,62,0.14)",  color: "var(--copper)", type: "Voice · Call" },
  voice_voicemail: { icon: Phone,              bg: "rgba(196,106,62,0.14)",  color: "var(--copper)", type: "Voice · Voicemail" },
  sms_sent:        { icon: MessageSquare,      bg: "rgba(12,10,8,0.05)",     color: "var(--ink-3)", type: "SMS · Sent" },
  sms_replied:     { icon: MessageSquareReply, bg: "rgba(107,142,90,0.16)",  color: "var(--green)", type: "SMS · Replied" },
  meeting_booked:  { icon: Calendar,           bg: "rgba(74,111,165,0.14)",  color: "var(--blue)",  type: "Meeting · Booked" },
};

function Timeline({ signals }: { signals: ProspectSignal[] }) {
  // Newest first
  const sorted = [...signals].sort(
    (a, b) => Date.parse(b.at) - Date.parse(a.at),
  );
  return (
    <ol className="space-y-2.5">
      {sorted.map(s => (
        <SignalRow key={s.id} signal={s} />
      ))}
    </ol>
  );
}

function SignalRow({ signal }: { signal: ProspectSignal }) {
  const def = SIGNAL_ICON[signal.kind];
  const Icon = def.icon;
  const time = new Date(signal.at);
  return (
    <li className="grid gap-3 rounded-[10px] border border-rule bg-panel px-4 py-3.5"
        style={{ gridTemplateColumns: "60px 38px 1fr" }}>
      <div className="font-mono text-[10.5px] text-ink-3 pt-1 whitespace-nowrap">
        {time.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
        <div className="opacity-70">
          {time.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>

      <div
        className="w-[38px] h-[38px] rounded-[10px] grid place-items-center"
        style={{ backgroundColor: def.bg, color: def.color }}
      >
        <Icon className="w-4 h-4" strokeWidth={1.6} />
      </div>

      <div className="min-w-0">
        <div className="font-mono text-[9.5px] tracking-[0.16em] uppercase font-semibold"
             style={{ color: "var(--copper)" }}>
          {def.type}
        </div>
        <div className="text-[14px] text-ink mt-0.5 leading-snug">
          {signal.headline}
        </div>
        {signal.quote && (
          <blockquote
            className="mt-2 font-display italic text-[14px] text-ink-2 leading-snug py-2 px-3 rounded-[0_6px_6px_0]"
            style={{
              backgroundColor: "var(--surface)",
              borderLeft: "3px solid var(--amber)",
            }}
          >
            “{signal.quote}”
          </blockquote>
        )}
      </div>
    </li>
  );
}

// ─── Meeting block — booking countdown ────────────────────────────────────

function MeetingBlock({ meeting }: { meeting: ProspectMeeting }) {
  const countdown = useMemo(() => {
    const ts = Date.parse(meeting.scheduledAt);
    if (Number.isNaN(ts)) return null;
    const diffMs = ts - Date.now();
    if (diffMs <= 0) return "in progress";
    const days  = Math.floor(diffMs / (24 * 3600 * 1000));
    const hours = Math.floor((diffMs % (24 * 3600 * 1000)) / (3600 * 1000));
    const mins  = Math.floor((diffMs % (3600 * 1000)) / 60000);
    if (days > 0) return `in ${days}d ${hours}h`;
    if (hours > 0) return `in ${hours}h ${mins}m`;
    return `in ${mins}m`;
  }, [meeting.scheduledAt]);

  const dt = new Date(meeting.scheduledAt);
  const dateLabel = dt.toLocaleDateString(undefined, {
    weekday: "long", month: "short", day: "numeric",
  });
  const timeLabel = dt.toLocaleTimeString(undefined, {
    hour: "2-digit", minute: "2-digit",
  });

  return (
    <div
      className="rounded-[8px] p-4"
      style={{
        backgroundColor: "rgba(107,142,90,0.10)",
        borderLeft: "3px solid var(--green)",
      }}
    >
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <div className="font-display font-bold text-[16px] text-ink">
            {dateLabel}
            <span className="text-ink-3"> · </span>
            <span className="font-mono text-[14px]">{timeLabel}</span>
          </div>
          {meeting.withName && (
            <div className="text-[12.5px] text-ink-2 mt-0.5">
              with {meeting.withName}
              {meeting.durationMin ? ` · ${meeting.durationMin} min` : ""}
            </div>
          )}
        </div>

        {countdown && (
          <span
            className="font-mono text-[11px] tracking-[0.08em] uppercase font-semibold"
            style={{ color: "var(--green)" }}
          >
            {countdown}
          </span>
        )}
      </div>

      {meeting.joinUrl && (
        <a
          href={meeting.joinUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block mt-3 font-mono text-[10px] tracking-[0.08em] uppercase font-semibold px-3 py-1.5 rounded-[4px]"
          style={{ backgroundColor: "var(--ink)", color: "white" }}
        >
          Join meeting →
        </a>
      )}
    </div>
  );
}
