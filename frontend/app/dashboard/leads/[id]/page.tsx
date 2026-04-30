/**
 * FILE: frontend/app/dashboard/leads/[id]/page.tsx
 * PURPOSE: Redirect from the legacy lead-detail route to the unified
 *          pipeline view, with the lead ID forwarded as a query
 *          parameter so the pipeline can auto-open the prospect
 *          drawer for that lead.
 * RETIRED: 2026-04-30 — P3 cleanup. The 571-line bespoke timeline
 *          view duplicated the prospect drawer. Pipeline now handles
 *          all lead detail surfaces.
 *
 * The original implementation lives in git history; recover with
 * `git show <prev-sha>:frontend/app/dashboard/leads/[id]/page.tsx`
 * if the bespoke timeline becomes interesting again.
 */

import { redirect } from "next/navigation";

interface Params { params: { id: string } }

export default function LegacyLeadRedirect({ params }: Params) {
  redirect(`/dashboard/pipeline?lead=${encodeURIComponent(params.id)}`);
}
