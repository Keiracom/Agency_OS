"use client";

/**
 * FILE: frontend/app/dashboard/approval/page.tsx
 * PURPOSE: Manual-mode approval queue route
 * PHASE: PHASE-2.1-APPROVAL-KILLSWITCH
 */

import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ApprovalQueue } from "@/components/dashboard/ApprovalQueue";
import { useApprovalQueue } from "@/lib/hooks/useApprovalQueue";

export default function ApprovalPage() {
  const { touches } = useApprovalQueue();
  return (
    <AppShell pageTitle="Approval">
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
        <header className="mb-4">
          <h1 className="font-serif text-2xl md:text-3xl text-gray-100">
            Approval queue{" "}
            <span className="text-gray-500 font-mono text-lg">({touches.length})</span>
          </h1>
          <p className="text-sm text-gray-400">
            Manual mode — review each queued touch before release.
          </p>
        </header>

        <ApprovalQueue />

        <nav className="mt-6 text-xs text-gray-500 font-mono flex gap-3">
          <Link href="/dashboard" className="hover:text-gray-300">← Home</Link>
          <Link href="/dashboard/pipeline" className="hover:text-gray-300">Pipeline →</Link>
          <Link href="/dashboard/activity" className="hover:text-gray-300">Activity →</Link>
        </nav>
      </div>
    </AppShell>
  );
}
