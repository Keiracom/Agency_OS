/**
 * FILE: frontend/plasmic-init.ts
 * PURPOSE: Initialize Plasmic loader for Agency OS dashboard
 * DOCS: https://docs.plasmic.app/learn/nextjs-quickstart/
 */

import { initPlasmicLoader } from "@plasmicapp/loader-nextjs";
import React from "react";

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
// Using React.lazy for code splitting

// Dashboard Components
PLASMIC.registerComponent(
  React.lazy(() => import("@/components/dashboard/HeroMetricsCard").then(m => ({ default: m.HeroMetricsCard }))),
  {
    name: "HeroMetricsCard",
    props: {
      className: "string",
    },
    importPath: "@/components/dashboard/HeroMetricsCard",
  }
);

PLASMIC.registerComponent(
  React.lazy(() => import("@/components/dashboard/LiveActivityFeed").then(m => ({ default: m.LiveActivityFeed }))),
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
  React.lazy(() => import("@/components/dashboard/meetings-widget").then(m => ({ default: m.MeetingsWidget }))),
  {
    name: "MeetingsWidget",
    props: {},
    importPath: "@/components/dashboard/meetings-widget",
  }
);

PLASMIC.registerComponent(
  React.lazy(() => import("@/components/dashboard/EmergencyPauseButton").then(m => ({ default: m.EmergencyPauseButton }))),
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
  React.lazy(() => import("@/components/dashboard/OnTrackIndicator").then(m => ({ default: m.OnTrackIndicator }))),
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
  React.lazy(() => import("@/components/dashboard/BestOfShowcase").then(m => ({ default: m.BestOfShowcase }))),
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
  React.lazy(() => import("@/components/campaigns/CampaignPriorityPanel").then(m => ({ default: m.CampaignPriorityPanel }))),
  {
    name: "CampaignPriorityPanel",
    props: {
      className: "string",
    },
    importPath: "@/components/campaigns/CampaignPriorityPanel",
  }
);

PLASMIC.registerComponent(
  React.lazy(() => import("@/components/campaigns/CampaignPriorityCard").then(m => ({ default: m.CampaignPriorityCard }))),
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
  React.lazy(() => import("@/components/campaigns/CampaignMetricsPanel").then(m => ({ default: m.CampaignMetricsPanel }))),
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
  React.lazy(() => import("@/components/leads/ALSScorecard").then(m => ({ default: m.ALSScorecard }))),
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
