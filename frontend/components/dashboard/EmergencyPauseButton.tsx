/**
 * FILE: frontend/components/dashboard/EmergencyPauseButton.tsx
 * PURPOSE: Emergency pause button for stopping all outreach
 * PHASE H: Item 43 - Emergency Pause Button
 * DATE: 2026-01-23
 */

"use client";

import { useState } from "react";
import { AlertTriangle, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { emergencyPauseAll, resumeAllOutreach } from "@/lib/api/campaigns";

interface EmergencyPauseButtonProps {
  clientId: string;
  isPaused?: boolean;
  pausedAt?: string | null;
  pauseReason?: string | null;
  onPauseChange?: (isPaused: boolean) => void;
}

export function EmergencyPauseButton({
  clientId,
  isPaused = false,
  pausedAt,
  pauseReason,
  onPauseChange,
}: EmergencyPauseButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [reason, setReason] = useState("");
  const { toast } = useToast();

  const handlePause = async () => {
    setIsLoading(true);
    try {
      const response = await emergencyPauseAll(clientId, reason || undefined);

      toast({
        title: "Outreach Paused",
        description: `All outreach has been paused. ${response.campaigns_affected} campaigns affected.`,
        variant: "destructive",
      });

      onPauseChange?.(true);
      setIsOpen(false);
      setReason("");
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to pause outreach. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try {
      await resumeAllOutreach(clientId);

      toast({
        title: "Outreach Resumed",
        description: "Emergency pause has been cleared. You can now reactivate campaigns.",
      });

      onPauseChange?.(false);
      setIsOpen(false);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to resume outreach. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isPaused) {
    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="border-yellow-500 text-yellow-600 hover:bg-yellow-50"
          >
            <Pause className="mr-2 h-4 w-4" />
            Paused
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Outreach is Paused
            </DialogTitle>
            <DialogDescription>
              All automated outreach is currently paused.
              {pausedAt && (
                <span className="block mt-2 text-sm">
                  Paused at: {new Date(pausedAt).toLocaleString()}
                </span>
              )}
              {pauseReason && (
                <span className="block mt-1 text-sm">
                  Reason: {pauseReason}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleResume} disabled={isLoading}>
              <Play className="mr-2 h-4 w-4" />
              {isLoading ? "Resuming..." : "Resume Outreach"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant="destructive"
          size="sm"
        >
          <Pause className="mr-2 h-4 w-4" />
          Emergency Pause
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Emergency Pause
          </DialogTitle>
          <DialogDescription>
            This will immediately stop ALL automated outreach including emails,
            SMS, LinkedIn messages, and voice calls. Use this if you need to
            stop all communications immediately.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Label htmlFor="reason">Reason (optional)</Label>
          <Textarea
            id="reason"
            placeholder="Why are you pausing outreach?"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="mt-2"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handlePause}
            disabled={isLoading}
          >
            <Pause className="mr-2 h-4 w-4" />
            {isLoading ? "Pausing..." : "Pause All Outreach"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
