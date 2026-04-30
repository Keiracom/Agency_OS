/**
 * FILE: frontend/components/layout/pause-all-button.tsx
 * PURPOSE: Consolidated "Pause all" button for the topbar — replaces
 *          KillSwitch.tsx + EmergencyPauseButton.tsx + (in-topbar use of)
 *          PauseCycleButton.tsx with one component.
 * REFERENCE: dashboard-master-agency-desk.html line 784 —
 *            <button class="kill-btn">⏸ Pause all</button>
 *
 * Behaviour:
 *   - Idle  → "⏸ Pause all" pill, hover amber
 *   - Click → confirm dialog → POST /api/v1/clients/{id}/pause-all
 *             via lib/api/campaigns.emergencyPauseAll (existing helper
 *             that the old EmergencyPauseButton already used — kept
 *             so backend semantics don't change)
 *   - Paused state → "⏵ Resume" pill (amber accent)
 *   - Mobile prop scales padding + hides the verb so it stays compact
 *     in the 52px MobileTopbar
 *
 * Auth: relies on the auth cookie via `credentials: 'include'` inside
 * the lib/api/campaigns helpers — no per-call auth wiring needed.
 */

"use client";

import { useState } from "react";
import { Pause, Play } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { emergencyPauseAll, resumeAllOutreach } from "@/lib/api/campaigns";
import { cn } from "@/lib/utils";

interface Props {
  /** Tenant client ID — required to scope the pause-all call. When
   *  undefined, the button renders disabled with a "no tenant" tooltip
   *  so demo / pre-login views don't crash. */
  clientId?: string;
  /** Initial paused state from server. */
  isPaused?: boolean;
  /** Optional ISO timestamp for tooltip context when paused. */
  pausedAt?: string | null;
  /** Optional reason from the prior pause action. */
  pauseReason?: string | null;
  /** Compact variant for the 52px mobile topbar. */
  compact?: boolean;
  /** Callback after successful state change. */
  onPauseChange?: (paused: boolean) => void;
}

export function PauseAllButton({
  clientId,
  isPaused = false,
  pausedAt,
  pauseReason,
  compact = false,
  onPauseChange,
}: Props) {
  const [paused, setPaused] = useState<boolean>(isPaused);
  const [reason, setReason] = useState("");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();

  const handleConfirmPause = async () => {
    if (!clientId) return;
    setBusy(true);
    try {
      await emergencyPauseAll(clientId, reason || "Pause all (operator)");
      setPaused(true);
      onPauseChange?.(true);
      toast({
        title: "All outreach paused",
        description: "Maya will not send anything until you resume.",
      });
      setOpen(false);
      setReason("");
    } catch (err) {
      toast({
        title: "Pause failed",
        description: err instanceof Error ? err.message : "Try again.",
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleResume = async () => {
    if (!clientId) return;
    setBusy(true);
    try {
      await resumeAllOutreach(clientId);
      setPaused(false);
      onPauseChange?.(false);
      toast({
        title: "Outreach resumed",
        description: "Maya is back to work.",
      });
    } catch (err) {
      toast({
        title: "Resume failed",
        description: err instanceof Error ? err.message : "Try again.",
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  // ─── Resume pill (paused state) ─────────────────────────────────
  if (paused) {
    return (
      <button
        type="button"
        disabled={busy || !clientId}
        onClick={handleResume}
        title={pauseReason ? `Paused${pausedAt ? ` at ${new Date(pausedAt).toLocaleString()}` : ""}: ${pauseReason}` : undefined}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-[6px]",
          "font-mono uppercase font-semibold tracking-[0.08em]",
          "bg-amber text-on-amber border border-amber",
          "hover:opacity-90 disabled:opacity-50 transition-opacity",
          compact ? "px-2.5 py-1 text-[10px]" : "px-3 py-1.5 text-[11px]",
        )}
      >
        <Play className={compact ? "w-3 h-3" : "w-3.5 h-3.5"} />
        {compact ? "" : "Resume"}
      </button>
    );
  }

  // ─── Pause pill (default state) ─────────────────────────────────
  return (
    <>
      <button
        type="button"
        disabled={busy || !clientId}
        onClick={() => setOpen(true)}
        title={!clientId ? "No tenant context — sign in to pause." : undefined}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-[6px]",
          "font-mono uppercase tracking-[0.08em]",
          "bg-transparent text-ink-2 border border-rule",
          "hover:text-red hover:border-red transition-colors",
          "disabled:opacity-40 disabled:cursor-not-allowed",
          compact ? "px-2.5 py-1 text-[10px]" : "px-3 py-1.5 text-[11px] font-semibold",
        )}
      >
        <Pause className={compact ? "w-3 h-3" : "w-3.5 h-3.5"} />
        {compact ? "" : "Pause all"}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display font-bold text-[20px] text-ink">
              Pause <em className="text-amber" style={{ fontStyle: "italic" }}>all</em> outreach?
            </DialogTitle>
            <DialogDescription className="text-[13px] text-ink-2 leading-relaxed mt-1">
              Maya will stop sending email, LinkedIn, voice, and SMS for
              every campaign on this account until you resume. Existing
              scheduled touches will not fire.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 mt-2">
            <Label htmlFor="pause-reason" className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3">
              Reason (optional)
            </Label>
            <Textarea
              id="pause-reason"
              placeholder="e.g. legal review, customer renegotiation, holiday freeze"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
            />
          </div>

          <DialogFooter className="gap-2 mt-2">
            <Button variant="ghost" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmPause}
              disabled={busy}
            >
              {busy ? "Pausing…" : "Pause all"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
