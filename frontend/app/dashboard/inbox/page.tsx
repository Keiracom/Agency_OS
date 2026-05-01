/**
 * FILE: frontend/app/dashboard/inbox/page.tsx
 * PURPOSE: Permanent redirect to canonical activity feed.
 * UPDATED: 2026-05-01 — B2.4 consolidation. Inbox view collapsed into
 *          /dashboard/activity. Channel chips replace the prior list +
 *          preview pane.
 */

import { redirect } from "next/navigation";

export default function InboxPage() {
  redirect("/dashboard/activity");
}
