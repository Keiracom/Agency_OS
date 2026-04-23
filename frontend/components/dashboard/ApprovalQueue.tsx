/**
 * FILE: frontend/components/dashboard/ApprovalQueue.tsx
 * PURPOSE: Manual-mode gate over scheduled_touches pending rows
 * PHASE: PHASE-2.1-APPROVAL-KILLSWITCH
 *
 * Operator reviews each queued touch and approves / rejects / defers / edits.
 * Batch actions: Release All, Review More (pagination), Release with Exceptions.
 * Channel filter + scheduled_at sort.
 *
 * The "approved" status lives in scheduled_touches.status; the hourly flow
 * gate enforcement is backend-side (out of scope for this PR). This component
 * is UI-only — mutations POST to /api/v1/outreach/approval.
 */

"use client";

import { useMemo, useState } from "react";
import {
  Mail, Linkedin, Phone, MessageSquare,
  Check, X as XIcon, Clock, Pencil,
} from "lucide-react";
import { useApprovalQueue, type PendingTouch } from "@/lib/hooks/useApprovalQueue";
import { canonicalChannel, providerLabel } from "@/lib/provider-labels";

type ChannelFilter = "all" | "email" | "linkedin" | "voice" | "sms";
const PAGE_SIZE = 10;

function channelIcon(channel: string) {
  const label = canonicalChannel(channel ?? "");
  const Icon =
    label === "Email"    ? Mail :
    label === "LinkedIn" ? Linkedin :
    label === "SMS"      ? MessageSquare :
    label === "Voice AI" ? Phone :
    Mail;
  return <Icon className="w-4 h-4 text-gray-400" strokeWidth={1.75} />;
}

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function ApprovalQueue() {
  const { touches, isLoading, approve, reject, defer, releaseAll } = useApprovalQueue();
  const [filter, setFilter] = useState<ChannelFilter>("all");
  const [page, setPage] = useState(1);
  const [localRejected, setLocalRejected] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<PendingTouch | null>(null);

  const filtered = useMemo(() => {
    const base = touches.filter((t) => {
      if (filter === "all") return true;
      return canonicalChannel(t.channel).toLowerCase().replace(" ai", "") === filter;
    });
    return base;
  }, [touches, filter]);

  const visible = useMemo(() => filtered.slice(0, page * PAGE_SIZE), [filtered, page]);

  const counts = useMemo(() => {
    const by: Record<string, number> = { all: touches.length, email: 0, linkedin: 0, voice: 0, sms: 0 };
    for (const t of touches) {
      const key = canonicalChannel(t.channel).toLowerCase().replace(" ai", "");
      if (key in by) by[key] += 1;
    }
    return by;
  }, [touches]);

  const onRelease = async () => {
    const ids = visible.filter((t) => !localRejected.has(t.id)).map((t) => t.id);
    await releaseAll.mutateAsync(ids);
    setLocalRejected(new Set());
  };

  const toggleReject = (id: string) => {
    setLocalRejected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  };

  return (
    <div className="space-y-4">
      {/* Filter + batch actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex flex-wrap gap-1.5">
          {(["all", "email", "linkedin", "voice", "sms"] as ChannelFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setPage(1); }}
              className={`px-3 py-1.5 text-[11px] font-mono uppercase tracking-widest rounded-md border ${
                filter === f
                  ? "bg-amber-500/10 text-amber-300 border-amber-500/40"
                  : "bg-gray-900 text-gray-400 border-gray-800 hover:text-gray-200"
              }`}
            >
              {f === "voice" ? "Voice AI" : f}
              <span className="ml-1.5 text-gray-500">{counts[f] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={visible.length >= filtered.length}
            className="px-3 py-1.5 text-[11px] font-mono uppercase tracking-widest rounded-md bg-gray-800 border border-gray-700 text-gray-200 hover:border-amber-500/40 disabled:opacity-40"
          >
            Review more
          </button>
          <button
            onClick={onRelease}
            disabled={releaseAll.isPending || visible.length === 0}
            className="px-3 py-1.5 text-[11px] font-mono uppercase tracking-widest rounded-md bg-emerald-600/20 border border-emerald-600/50 text-emerald-200 hover:bg-emerald-600/30 disabled:opacity-40"
          >
            {localRejected.size > 0 ? "Release with exceptions" : "Release all"}
          </button>
        </div>
      </div>

      {/* Queue */}
      {isLoading ? (
        <div className="text-sm text-gray-500 italic py-10 text-center">
          Loading queue…
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-10 text-center text-sm text-gray-400">
          Queue is clear — no pending touches need approval.
        </div>
      ) : (
        <ul className="divide-y divide-gray-800 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {visible.map((t) => {
            const rejected = localRejected.has(t.id);
            return (
              <li
                key={t.id}
                className={`px-4 py-3 flex items-start gap-3 ${
                  rejected ? "opacity-50 line-through" : ""
                }`}
              >
                <span className="shrink-0 mt-0.5">{channelIcon(t.channel)}</span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2">
                    <span className="text-sm text-gray-100 truncate">
                      {t.prospectName}
                    </span>
                    <span className="text-xs text-gray-500 truncate">
                      · {t.company}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-500 font-mono mt-0.5">
                    {canonicalChannel(t.channel)}
                    {t.sequenceStep ? <span> · step {t.sequenceStep}</span> : null}
                    <span> · {fmt(t.scheduledAt)}</span>
                  </div>
                  {t.contentPreview && (
                    <div className="text-xs text-gray-400 mt-1 line-clamp-2 italic">
                      &ldquo;{providerLabel(t.contentPreview)}&rdquo;
                    </div>
                  )}
                </div>

                <div className="flex gap-1.5 shrink-0">
                  <ActionBtn
                    title="Approve" color="emerald"
                    icon={<Check className="w-3.5 h-3.5" />}
                    loading={approve.isPending}
                    onClick={() => approve.mutate(t.id)}
                  />
                  <ActionBtn
                    title="Edit" color="gray"
                    icon={<Pencil className="w-3.5 h-3.5" />}
                    onClick={() => setEditing(t)}
                  />
                  <ActionBtn
                    title="Defer 24h" color="amber"
                    icon={<Clock className="w-3.5 h-3.5" />}
                    loading={defer.isPending}
                    onClick={() => defer.mutate(t.id)}
                  />
                  <ActionBtn
                    title={rejected ? "Undo reject" : "Reject"}
                    color="red"
                    icon={<XIcon className="w-3.5 h-3.5" />}
                    loading={reject.isPending}
                    onClick={() => {
                      toggleReject(t.id);
                      if (!rejected) reject.mutate(t.id);
                    }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {editing && (
        <EditModal touch={editing} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}

function ActionBtn({
  title, icon, onClick, loading, color,
}: {
  title: string; icon: React.ReactNode; onClick: () => void;
  loading?: boolean;
  color: "emerald" | "red" | "amber" | "gray";
}) {
  const styles: Record<string, string> = {
    emerald: "bg-emerald-600/10 border-emerald-600/40 text-emerald-300 hover:bg-emerald-600/20",
    red:     "bg-red-500/10 border-red-500/40 text-red-300 hover:bg-red-500/20",
    amber:   "bg-amber-500/10 border-amber-500/40 text-amber-300 hover:bg-amber-500/20",
    gray:    "bg-gray-800 border-gray-700 text-gray-300 hover:border-amber-500/40",
  };
  return (
    <button
      onClick={onClick}
      disabled={loading}
      title={title}
      aria-label={title}
      className={`border rounded-md px-2 py-1.5 text-[11px] font-medium transition disabled:opacity-40 ${styles[color]}`}
    >
      {icon}
    </button>
  );
}

function EditModal({ touch, onClose }: { touch: PendingTouch; onClose: () => void }) {
  const [text, setText] = useState(touch.contentPreview ?? "");
  return (
    <div className="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
         onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-gray-900 border border-gray-800 rounded-xl p-5 w-full max-w-lg"
      >
        <div className="font-mono text-[10px] uppercase tracking-widest text-gray-500 mb-1">
          Edit touch content
        </div>
        <div className="text-sm text-gray-200 mb-3">
          {touch.prospectName} · {canonicalChannel(touch.channel)}
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full h-40 bg-gray-950 border border-gray-700 rounded-lg p-3 text-sm text-gray-100 font-mono"
          placeholder="Content preview…"
        />
        <div className="flex justify-end gap-2 mt-3">
          <button onClick={onClose} className="px-3 py-1.5 text-xs rounded-md bg-gray-800 text-gray-300 border border-gray-700">
            Cancel
          </button>
          <button
            onClick={async () => {
              try {
                await fetch("/api/v1/outreach/approval", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    touch_id: touch.id, action: "edit", content: { preview: text },
                  }),
                });
              } catch (e) {
                console.error("[ApprovalQueue] edit failed", e);
              }
              onClose();
            }}
            className="px-3 py-1.5 text-xs rounded-md bg-amber-500/15 border border-amber-500/50 text-amber-200"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
