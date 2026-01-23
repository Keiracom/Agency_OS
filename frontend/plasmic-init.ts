/**
 * FILE: frontend/plasmic-init.ts
 * PURPOSE: Initialize Plasmic loader for Agency OS dashboard
 * DOCS: https://docs.plasmic.app/learn/nextjs-quickstart/
 */

import { initPlasmicLoader } from "@plasmicapp/loader-nextjs";

export const PLASMIC = initPlasmicLoader({
  projects: [
    {
      id: process.env.NEXT_PUBLIC_PLASMIC_PROJECT_ID!,
      token: process.env.NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN!,
    },
  ],
  // Enable preview mode for live updates in development
  preview: process.env.NODE_ENV === "development",
});

// Register code components that Plasmic can use
// These are the existing React components from our codebase

// Dashboard Components
PLASMIC.registerComponent(
  async () => (await import("@/components/dashboard/HeroMetricsCard")).HeroMetricsCard,
  {
    name: "HeroMetricsCard",
    props: {
      className: "string",
    },
    importPath: "@/components/dashboard/HeroMetricsCard",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/dashboard/LiveActivityFeed")).LiveActivityFeed,
  {
    name: "LiveActivityFeed",
    props: {
      maxItems: "number",
      showLoadMore: "boolean",
      className: "string",
    },
    importPath: "@/components/dashboard/LiveActivityFeed",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/dashboard/meetings-widget")).MeetingsWidget,
  {
    name: "MeetingsWidget",
    props: {},
    importPath: "@/components/dashboard/meetings-widget",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/dashboard/EmergencyPauseButton")).EmergencyPauseButton,
  {
    name: "EmergencyPauseButton",
    props: {
      variant: {
        type: "choice",
        options: ["default", "compact"],
      },
    },
    importPath: "@/components/dashboard/EmergencyPauseButton",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/dashboard/OnTrackIndicator")).OnTrackIndicator,
  {
    name: "OnTrackIndicator",
    props: {
      status: {
        type: "choice",
        options: ["ahead", "on_track", "behind"],
      },
      targetLow: "number",
      targetHigh: "number",
      current: "number",
    },
    importPath: "@/components/dashboard/OnTrackIndicator",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/dashboard/BestOfShowcase")).BestOfShowcase,
  {
    name: "BestOfShowcase",
    props: {
      className: "string",
    },
    importPath: "@/components/dashboard/BestOfShowcase",
  }
);

// Campaign Components
PLASMIC.registerComponent(
  async () => (await import("@/components/campaigns/CampaignPriorityPanel")).CampaignPriorityPanel,
  {
    name: "CampaignPriorityPanel",
    props: {
      className: "string",
    },
    importPath: "@/components/campaigns/CampaignPriorityPanel",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/campaigns/CampaignPriorityCard")).CampaignPriorityCard,
  {
    name: "CampaignPriorityCard",
    props: {
      campaign: "object",
      priority: "number",
      onPriorityChange: {
        type: "eventHandler",
        argTypes: [{ name: "value", type: "number" }],
      },
    },
    importPath: "@/components/campaigns/CampaignPriorityCard",
  }
);

PLASMIC.registerComponent(
  async () => (await import("@/components/campaigns/CampaignMetricsPanel")).CampaignMetricsPanel,
  {
    name: "CampaignMetricsPanel",
    props: {
      campaignId: "string",
      className: "string",
    },
    importPath: "@/components/campaigns/CampaignMetricsPanel",
  }
);

// Lead Components
PLASMIC.registerComponent(
  async () => (await import("@/components/leads/ALSScorecard")).ALSScorecard,
  {
    name: "ALSScorecard",
    props: {
      score: "number",
      breakdown: "object",
      showBadge: "boolean",
      size: {
        type: "choice",
        options: ["sm", "md", "lg"],
      },
    },
    importPath: "@/components/leads/ALSScorecard",
  }
);
