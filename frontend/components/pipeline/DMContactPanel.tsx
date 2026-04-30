"use client";

/**
 * FILE: components/pipeline/DMContactPanel.tsx
 * PURPOSE: Compact DM contact panel — all channels with status badges
 */

import { useState } from "react";
import { Mail, Phone, Linkedin, Copy, ExternalLink, FileText } from "lucide-react";
import type { ProspectCard } from "@/lib/types/prospect-card";

interface DMContactPanelProps {
  card: ProspectCard;
}

function ConfidenceBadge({ confidence }: { confidence: string | null }) {
  if (!confidence) return null;
  const upper = confidence.toUpperCase();
  const color =
    upper === "HIGH"
      ? "text-[#10B981] bg-[#10B981]/10 border-[#10B981]/30"
      : upper === "MEDIUM"
      ? "text-amber bg-amber-glow border-amber/30"
      : "text-ink-3 bg-bg-elevated border-rule";
  return (
    <span
      className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border uppercase tracking-wide ${color}`}
    >
      {upper}
    </span>
  );
}

function SourceBadge({ source }: { source: string | null }) {
  if (!source) return null;
  const labels: Record<string, string> = {
    html: "HTML",
    pattern: "Pattern",
    leadmagic: "Leadmagic",
    bd: "BD",
    smtp: "SMTP",
    apollo: "Apollo",
  };
  const label = labels[source.toLowerCase()] ?? source.toUpperCase().slice(0, 8);
  return (
    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-elevated text-ink-3 border border-rule">
      {label}
    </span>
  );
}

export function DMContactPanel({ card }: DMContactPanelProps) {
  const [copied, setCopied] = useState<string | null>(null);

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const copyDraft = async () => {
    const subject = card.draft_email_subject ?? "";
    const body = card.draft_email_body ?? "";
    const text = subject ? `Subject: ${subject}\n\n${body}` : body;
    if (text) await copyToClipboard(text, "draft");
  };

  const hasDM = card.dm_name || card.dm_email || card.dm_mobile || card.dm_linkedin_url;

  if (!hasDM) {
    return (
      <div className="p-3 rounded-lg bg-bg-elevated border border-rule">
        <p className="text-xs text-ink-3 font-mono">DM not identified</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-bg-elevated border border-rule overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-rule flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-amber-glow flex items-center justify-center text-amber text-xs font-bold">
          {card.dm_name ? card.dm_name[0].toUpperCase() : "?"}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-ink truncate">
              {card.dm_name ?? "Unknown"}
            </span>
            <ConfidenceBadge confidence={card.dm_confidence} />
          </div>
          {card.dm_title && (
            <div className="text-xs text-ink-3 truncate">{card.dm_title}</div>
          )}
        </div>
      </div>

      {/* Contact rows */}
      <div className="px-3 py-2 space-y-1.5">
        {/* Email */}
        {card.dm_email && (
          <div className="flex items-center gap-2">
            <Mail className="w-3.5 h-3.5 text-ink-3 flex-shrink-0" strokeWidth={1.5} />
            <span className="text-xs font-mono text-ink-2 flex-1 truncate">
              {card.dm_email}
            </span>
            <div className="flex items-center gap-1 flex-shrink-0">
              {card.dm_email_verified && (
                <span className="text-[10px] font-mono font-semibold text-[#10B981] bg-[#10B981]/10 border border-[#10B981]/30 px-1.5 py-0.5 rounded">
                  ✓ SMTP
                </span>
              )}
              <SourceBadge source={card.dm_email_source} />
            </div>
          </div>
        )}

        {/* Mobile */}
        {card.dm_mobile && (
          <div className="flex items-center gap-2">
            <Phone className="w-3.5 h-3.5 text-ink-3 flex-shrink-0" strokeWidth={1.5} />
            <span className="text-xs font-mono text-ink-2">{card.dm_mobile}</span>
          </div>
        )}

        {/* LinkedIn */}
        {card.dm_linkedin_url && (
          <div className="flex items-center gap-2">
            <Linkedin className="w-3.5 h-3.5 text-ink-3 flex-shrink-0" strokeWidth={1.5} />
            <span className="text-xs font-mono text-ink-2 truncate flex-1">
              {card.dm_linkedin_url.replace(/^https?:\/\/(www\.)?linkedin\.com\/in\//, "")}
            </span>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="px-3 pb-3 flex gap-2">
        {card.dm_email && (
          <button
            onClick={() => copyToClipboard(card.dm_email!, "email")}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono rounded bg-bg-panel border border-rule text-ink-2 hover:text-amber hover:border-amber/30 transition-colors"
          >
            <Copy className="w-3 h-3" />
            {copied === "email" ? "Copied!" : "Copy Email"}
          </button>
        )}
        {card.dm_linkedin_url && (
          <a
            href={card.dm_linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono rounded bg-bg-panel border border-rule text-ink-2 hover:text-amber hover:border-amber/30 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            LinkedIn
          </a>
        )}
        {(card.draft_email_subject || card.draft_email_body) && (
          <button
            onClick={copyDraft}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono rounded bg-amber-glow border border-amber/30 text-amber hover:bg-amber/15 transition-colors"
          >
            <FileText className="w-3 h-3" />
            {copied === "draft" ? "Copied!" : "Draft"}
          </button>
        )}
      </div>
    </div>
  );
}
