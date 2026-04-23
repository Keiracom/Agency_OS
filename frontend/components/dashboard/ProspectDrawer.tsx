/**
 * FILE: frontend/components/dashboard/ProspectDrawer.tsx
 * PURPOSE: Right-slide drawer showing full prospect state (contact, enrichment, timeline, actions)
 * PHASE: PHASE-2.1-PROSPECT-DRAWER-FEED
 *
 * Triggered by click on any prospect in Kanban/Table/Feed/Attention/Meetings.
 * Close on backdrop click, X button, or Escape key.
 * Desktop: 400px slide-from-right. Mobile: full-screen overlay.
 *
 * Quick actions (Pause/Skip/Suppress) POST to the webhook layer so the
 * CadenceDecisionTree produces the mutations. Best-effort — UI shows
 * optimistic feedback, errors surface inline.
 */

"use client";

import { useEffect, useState } from "react";
import {
  X, Mail, Linkedin, Phone, ExternalLink,
  PauseCircle, SkipForward, Ban,
} from "lucide-react";
import { useProspectDetail } from "@/lib/hooks/useProspectDetail";
import { useOutreachTimeline } from "@/lib/hooks/useOutreachTimeline";
import { OutreachTimeline } from "./OutreachTimeline";
import { VRGradePopover } from "./VRGradePopover";

interface Props {
  leadId: string | null;
  onClose: () => void;
}

export function ProspectDrawer({ leadId, onClose }: Props) {
  const { prospect, isLoading } = useProspectDetail(leadId);
  const timeline = useOutreachTimeline(prospect);
  const [actionState, setActionState] = useState<string | null>(null);

  // Escape closes drawer
  useEffect(() => {
    if (!leadId) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [leadId, onClose]);

  if (!leadId) return null;

  const runAction = async (kind: "pause" | "skip" | "suppress") => {
    if (!prospect) return;
    setActionState(`${kind}:pending`);
    try {
      const res = await fetch("/api/outreach/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_id: prospect.leadId, action: kind }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setActionState(`${kind}:ok`);
    } catch (e) {
      console.error("[ProspectDrawer] action failed", e);
      setActionState(`${kind}:error`);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60"
      onClick={onClose}
      role="presentation"
    >
      <aside
        onClick={(e) => e.stopPropagation()}
        className="absolute right-0 top-0 h-full w-full sm:w-[420px] bg-gray-950 border-l border-gray-800 overflow-y-auto animate-in slide-in-from-right duration-200"
        role="dialog"
        aria-label="Prospect detail"
      >
        <header className="sticky top-0 bg-gray-950/95 backdrop-blur border-b border-gray-800 px-5 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500">
              Prospect
            </div>
            <h2 className="font-serif text-xl text-gray-100 truncate">
              {prospect?.name ?? (isLoading ? "Loading…" : "—")}
            </h2>
            <div className="text-sm text-gray-400 truncate">{prospect?.company ?? ""}</div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {prospect?.vrGrade && (
              <VRGradePopover
                grade={prospect.vrGrade}
                score={prospect.score}
                vr={prospect.vr}
                evidence={buildEvidence(prospect)}
              />
            )}
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-200 p-1"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </header>

        {!prospect ? (
          <div className="p-5 text-sm text-gray-500 italic">
            {isLoading ? "Loading prospect…" : "Prospect not found."}
          </div>
        ) : (
          <div className="p-5 space-y-6">
            {/* Contact */}
            <Section title="Contact">
              <ContactRow icon={<Mail className="w-3.5 h-3.5" />} label="Email" value={prospect.contact.email} />
              <ContactRow icon={<Phone className="w-3.5 h-3.5" />} label="Phone" value={prospect.contact.phone} />
              <ContactRow
                icon={<Linkedin className="w-3.5 h-3.5" />} label="LinkedIn"
                value={prospect.contact.linkedinUrl} href={prospect.contact.linkedinUrl}
              />
            </Section>

            {/* Enrichment */}
            <Section title="Enrichment">
              <KV label="ABN"      value={prospect.enrichment.abn} />
              <KV label="Industry" value={prospect.enrichment.industry} />
              <KV label="Staff"    value={prospect.enrichment.employeeCount?.toString() ?? null} />
              <KV label="Website"  value={prospect.enrichment.website} href={prospect.enrichment.website} />
              <KV label="Location" value={prospect.enrichment.location} />
            </Section>

            {/* Unified outreach timeline */}
            <Section title="Outreach timeline">
              <OutreachTimeline events={timeline} isLoading={isLoading} />
            </Section>

            {/* Quick actions */}
            <Section title="Quick actions">
              <div className="grid grid-cols-3 gap-2">
                <ActionButton
                  icon={<PauseCircle className="w-4 h-4" />} label="Pause cadence"
                  onClick={() => runAction("pause")}
                  state={actionState?.startsWith("pause:") ? actionState : null}
                />
                <ActionButton
                  icon={<SkipForward className="w-4 h-4" />} label="Skip next"
                  onClick={() => runAction("skip")}
                  state={actionState?.startsWith("skip:") ? actionState : null}
                />
                <ActionButton
                  icon={<Ban className="w-4 h-4" />} label="Suppress"
                  onClick={() => runAction("suppress")}
                  state={actionState?.startsWith("suppress:") ? actionState : null}
                  danger
                />
              </div>
            </Section>
          </div>
        )}
      </aside>
    </div>
  );
}

// ---------- helpers --------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500 mb-2">
        {title}
      </div>
      <div className="space-y-1.5">{children}</div>
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="text-xs text-gray-500 italic">{children}</div>;
}

function KV({ label, value, href }: { label: string; value: string | null; href?: string | null }) {
  return (
    <div className="flex justify-between gap-3 text-sm">
      <span className="text-gray-500 font-mono text-[11px] uppercase">{label}</span>
      {value ? (
        href ? (
          <a href={href} target="_blank" rel="noreferrer"
             className="text-amber-300 hover:underline truncate max-w-[220px]">{value}</a>
        ) : (
          <span className="text-gray-200 truncate max-w-[220px]">{value}</span>
        )
      ) : (
        <span className="text-gray-600">—</span>
      )}
    </div>
  );
}

function ContactRow({
  icon, label, value, href,
}: { icon: React.ReactNode; label: string; value: string | null; href?: string | null }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-gray-500">{icon}</span>
      <span className="font-mono text-[10px] uppercase tracking-widest text-gray-500 w-16">{label}</span>
      {value ? (
        href ? (
          <a href={href} target="_blank" rel="noreferrer"
             className="text-amber-300 hover:underline truncate inline-flex items-center gap-1">
            {value}<ExternalLink className="w-3 h-3" />
          </a>
        ) : (
          <span className="text-gray-100 truncate">{value}</span>
        )
      ) : (
        <span className="text-gray-600">—</span>
      )}
    </div>
  );
}

function buildEvidence(p: {
  enrichment: { industry: string | null; employeeCount: number | null; location: string | null };
  touches: Array<{ replied: boolean }>;
}): string[] {
  const out: string[] = [];
  if (p.enrichment.industry) out.push(`Industry: ${p.enrichment.industry}`);
  if (p.enrichment.employeeCount) out.push(`Staff: ${p.enrichment.employeeCount}`);
  if (p.enrichment.location) out.push(`Based in ${p.enrichment.location}`);
  const replies = p.touches.filter((t) => t.replied).length;
  if (replies > 0) out.push(`${replies} reply${replies > 1 ? "s" : ""} recorded`);
  return out;
}

function ActionButton({
  icon, label, onClick, state, danger,
}: {
  icon: React.ReactNode; label: string; onClick: () => void;
  state: string | null; danger?: boolean;
}) {
  const pending = state?.endsWith(":pending");
  const ok = state?.endsWith(":ok");
  const err = state?.endsWith(":error");
  const base = danger
    ? "bg-red-500/10 border-red-500/40 text-red-300 hover:bg-red-500/20"
    : "bg-gray-800 border-gray-700 text-gray-200 hover:border-amber-500/50";
  return (
    <button
      onClick={onClick}
      disabled={pending}
      className={`border rounded-lg p-2 text-[11px] font-medium flex flex-col items-center gap-1 transition ${base} disabled:opacity-50`}
    >
      {icon}
      <span>{pending ? "…" : ok ? "Done" : err ? "Retry" : label}</span>
    </button>
  );
}
