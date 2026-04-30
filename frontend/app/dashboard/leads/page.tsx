/**
 * FILE: frontend/app/dashboard/leads/page.tsx
 * PURPOSE: Redirect from the legacy Leads scoreboard to the unified
 *          pipeline view (table mode).
 * RETIRED: 2026-04-30 — B2.2 dedupe per ORION O4. /leads and /pipeline
 *          showed the same prospect data in different layouts; one
 *          mental model is better than two. The bespoke 658-line
 *          scoreboard (animated SplitFlap counters, ALS row component,
 *          intent-tier filter chips) duplicated functionality already
 *          present in /pipeline's table view.
 *
 * Original implementation preserved in git history. Recover with
 * `git show <prev-sha>:frontend/app/dashboard/leads/page.tsx` if the
 * scoreboard treatment is wanted again.
 */

import { redirect } from "next/navigation";

export default function LeadsRedirect() {
  redirect("/dashboard/pipeline?view=table");
}
