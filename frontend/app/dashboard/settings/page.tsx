"use client";

/**
 * FILE: frontend/app/dashboard/settings/page.tsx
 * PURPOSE: Settings index — card grid pointing at the four working
 *          sub-pages. Each sub-page handles its own data wiring against
 *          real Supabase / FastAPI sources.
 *
 *          Replaces the prior tabbed mock-driven hub (consumed
 *          lib/mock/settings-data.ts; descoped 2026-05-09 per Tier 4
 *          analysis in docs/audits/aiden/tier4_wiring_vs_descope_2026-05-09.md
 *          — client_integrations and notification_preferences tables
 *          don't exist in prod schema, so the tabbed hub couldn't be
 *          honestly wired without parallel schema work).
 */

import Link from "next/link";
import { User, Bell, Target, Linkedin } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SettingsHeader } from "@/components/settings";

interface SettingsCard {
  title: string;
  description: string;
  href: string;
  Icon: typeof User;
}

const CARDS: SettingsCard[] = [
  {
    title: "Profile",
    description: "Your account name, email, and password.",
    href: "/dashboard/settings/profile",
    Icon: User,
  },
  {
    title: "Notifications",
    description: "Choose what events you want to be alerted about.",
    href: "/dashboard/settings/notifications",
    Icon: Bell,
  },
  {
    title: "ICP",
    description: "Ideal customer profile — who your campaigns target.",
    href: "/dashboard/settings/icp",
    Icon: Target,
  },
  {
    title: "LinkedIn",
    description: "Connect and manage your LinkedIn outreach account.",
    href: "/dashboard/settings/linkedin",
    Icon: Linkedin,
  },
];

export default function SettingsPage() {
  return (
    <AppShell pageTitle="Settings">
      <div className="max-w-4xl mx-auto">
        <SettingsHeader />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {CARDS.map((card) => {
            const Icon = card.Icon;
            return (
              <Link
                key={card.href}
                href={card.href}
                className="group block bg-panel border border-default rounded-xl p-6 transition-colors hover:border-amber"
              >
                <div className="flex items-start gap-4">
                  <div className="rounded-lg p-2.5 bg-amber-soft text-copper shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-ink group-hover:text-copper">
                      {card.title}
                    </h2>
                    <p className="text-sm text-ink-3 mt-1">
                      {card.description}
                    </p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
