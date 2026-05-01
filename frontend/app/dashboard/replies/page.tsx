/**
 * FILE: frontend/app/dashboard/replies/page.tsx
 * PURPOSE: Permanent redirect to canonical activity feed.
 * UPDATED: 2026-05-01 — B2.4 consolidation. The standalone replies inbox
 *          collapsed into /dashboard/activity (filter chip: Email).
 */

import { redirect } from "next/navigation";

export default function RepliesPage() {
  redirect("/dashboard/activity");
}
