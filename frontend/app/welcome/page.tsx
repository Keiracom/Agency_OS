"use client";

/**
 * FILE: frontend/app/welcome/page.tsx
 * PURPOSE: Retired in A7 (2026-04-30). The 862-line founding-member
 *          welcome surface has been folded into the onboarding flow.
 *          This stub now resolves the user's state and forwards them
 *          to the right next step:
 *            no subscription paid          → /
 *            paid, onboarding incomplete   → /onboarding/crm
 *            paid, onboarding complete     → /dashboard
 *          Demo viewers (?demo=true cookie) → /onboarding/step-1?demo=true
 *
 *          The previous celebratory copy + tier card + position
 *          counter are out of scope for the dashboard rebuild — they
 *          can return as a reusable section in the marketing site if
 *          the founding-member program ships again.
 *
 * GIT HISTORY: full prior implementation lives at the commit before
 *              this PR; recover with `git show <prev-sha>:frontend/
 *              app/welcome/page.tsx` if needed.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createBrowserClient } from "@/lib/supabase";

export default function WelcomeRedirect() {
  const router = useRouter();
  const supabase = createBrowserClient();

  useEffect(() => {
    let cancelled = false;
    async function decide() {
      try {
        // Demo cookie short-circuit — investors don't have a Supabase
        // session, but the dashboard demo flow lives behind onboarding
        // step-1 with ?demo=true.
        if (typeof document !== "undefined") {
          const cookie = document.cookie
            .split("; ")
            .find((row) => row.startsWith("agency_os_demo="));
          if (cookie?.split("=")[1] === "true") {
            router.replace("/onboarding/step-1?demo=true");
            return;
          }
        }

        const { data: { user } } = await supabase.auth.getUser();
        if (cancelled) return;
        if (!user) { router.replace("/"); return; }

        // Look up the user's primary client + onboarding state
        const { data: membership } = await supabase
          .from("memberships")
          .select("client_id, clients(id, name, deposit_paid)")
          .eq("user_id", user.id)
          .eq("role", "owner")
          .single();
        if (cancelled) return;
        if (!membership || !(membership as Record<string, unknown>).clients) {
          router.replace("/"); return;
        }

        const clientRow = (membership as Record<string, unknown>).clients as {
          id: string; deposit_paid: boolean;
        };
        if (!clientRow.deposit_paid) { router.replace("/"); return; }

        const { data: onboarding } = await supabase
          .from("clients")
          .select("website_url, icp_extracted")
          .eq("id", clientRow.id)
          .single();
        if (cancelled) return;

        const ob = onboarding as Record<string, unknown> | null;
        const onboardingComplete = ob?.website_url && ob?.icp_extracted;
        router.replace(onboardingComplete ? "/dashboard" : "/onboarding/crm");
      } catch {
        if (!cancelled) router.replace("/");
      }
    }
    decide();
    return () => { cancelled = true; };
  }, [router, supabase]);

  // Minimal placeholder while the redirect resolves — cream + amber
  // chrome consistent with the rest of the auth/onboarding flow.
  return (
    <div className="min-h-screen flex items-center justify-center bg-cream text-ink">
      <div className="text-center">
        <div className="font-display font-bold text-[24px] tracking-[-0.02em] text-ink">
          Agency<em className="text-amber" style={{ fontStyle: "italic" }}>OS</em>
        </div>
        <p className="mt-2 font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3">
          Loading your next step…
        </p>
      </div>
    </div>
  );
}
