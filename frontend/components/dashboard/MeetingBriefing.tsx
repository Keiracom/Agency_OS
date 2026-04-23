/**
 * FILE: frontend/components/dashboard/MeetingBriefing.tsx
 * PURPOSE: Pre-meeting briefing card — prospect summary + outreach history + talking points
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Dark theme, Tailwind only. All provider-facing text scrubbed via provider-labels.
 */

"use client";

import { useEffect, useState } from "react";
import { Mail, Linkedin, Phone, MessageSquare, ExternalLink, X } from "lucide-react";
import { MeetingRow } from "@/lib/hooks/useMeetingsData";
import { canonicalChannel, providerLabel } from "@/lib/provider-labels";
import { createBrowserClient } from "@/lib/supabase";

interface TouchSummary {
  id: string;
  channel: string;
  sent_at: string;
  replied: boolean;
  sequence_step: number | null;
}

interface Props {
  meeting: MeetingRow | null;
  onClose: () => void;
}

function channelIcon(channel: string | null) {
  const label = canonicalChannel(channel ?? "");
  const Icon =
    label === "Email"    ? Mail :
    label === "LinkedIn" ? Linkedin :
    label === "SMS"      ? MessageSquare :
    label === "Voice AI" ? Phone :
    Mail;
  return <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />;
}

async function loadTouches(leadId: string): Promise<TouchSummary[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  try {
    const { data } = await client
      .from("cis_outreach_outcomes")
      .select("id, channel, sent_at, replied_at, sequence_step")
      .eq("lead_id", leadId)
      .order("sent_at", { ascending: true });
    return ((data ?? []) as Array<{
      id: string; channel: string; sent_at: string;
      replied_at: string | null; sequence_step: number | null;
    }>).map((r) => ({
      id: r.id,
      channel: r.channel,
      sent_at: r.sent_at,
      replied: !!r.replied_at,
      sequence_step: r.sequence_step,
    }));
  } catch (e) {
    console.error("[MeetingBriefing] touches load failed", e);
    return [];
  }
}

export function MeetingBriefing({ meeting, onClose }: Props) {
  const [touches, setTouches] = useState<TouchSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!meeting) return;
    setLoading(true);
    loadTouches(meeting.leadId).then((t) => {
      setTouches(t);
      setLoading(false);
    });
  }, [meeting]);

  if (!meeting) return null;

  const when = meeting.scheduledAt ? new Date(meeting.scheduledAt) : null;
  const scrubbedNotes = meeting.notes ? providerLabel(meeting.notes) : null;

  return (
    <div className="fixed inset-0 bg-black/70 z-40 flex items-start justify-center p-4 md:p-8 overflow-y-auto">
      <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-2xl p-5 md:p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500 mb-1">
              Meeting briefing
            </div>
            <h2 className="font-serif text-xl text-gray-100">{meeting.dmName}</h2>
            <div className="text-sm text-gray-400">
              {meeting.dmTitle && <span>{meeting.dmTitle} · </span>}
              {meeting.company}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-200 p-1"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Meeting metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <Meta label="When" value={when ? when.toLocaleString() : "TBD"} />
          <Meta label="Type" value={meeting.meetingType ?? "—"} />
          <Meta label="VR" value={meeting.vrGrade ?? "—"} accent={!!meeting.vrGrade} />
          <Meta label="Score" value={meeting.score?.toString() ?? "—"} />
        </div>

        {/* Outreach history */}
        <section className="mb-5">
          <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500 mb-2">
            Outreach history
          </div>
          {loading ? (
            <div className="text-xs text-gray-500 italic">Loading touches…</div>
          ) : touches.length === 0 ? (
            <div className="text-xs text-gray-500 italic">No touches recorded</div>
          ) : (
            <ul className="space-y-1.5">
              {touches.map((t) => (
                <li key={t.id} className="flex items-center gap-2 text-xs text-gray-300">
                  {channelIcon(t.channel)}
                  <span className="font-mono text-gray-400 w-16">
                    {canonicalChannel(t.channel)}
                  </span>
                  <span className="text-gray-500">
                    {new Date(t.sent_at).toLocaleDateString()}
                  </span>
                  {t.replied && (
                    <span className="text-emerald-400 text-[10px] font-mono uppercase tracking-wider">
                      · replied
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Talking points (derived from notes; empty state if absent) */}
        <section className="mb-5">
          <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500 mb-2">
            Talking points
          </div>
          {scrubbedNotes ? (
            <div className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
              {scrubbedNotes}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">
              No enrichment notes yet. Add context before the call.
            </div>
          )}
        </section>

        {/* Meeting link */}
        {meeting.meetingLink && (
          <a
            href={meeting.meetingLink}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/50 text-amber-300 rounded-lg px-3 py-2 text-sm hover:bg-amber-500/20"
          >
            <ExternalLink className="w-4 h-4" />
            Join meeting
          </a>
        )}
      </div>
    </div>
  );
}

function Meta({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-2">
      <div className="font-mono text-[9px] tracking-widest uppercase text-gray-500">{label}</div>
      <div className={`text-sm mt-0.5 ${accent ? "text-amber-300 font-bold" : "text-gray-100"}`}>
        {value}
      </div>
    </div>
  );
}
