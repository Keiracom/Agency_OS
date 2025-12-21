/**
 * FILE: frontend/components/campaigns/permission-mode-selector.tsx
 * PURPOSE: Permission mode selector component
 * PHASE: 8 (Frontend)
 * TASK: FE-015
 */

"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Zap, Users, Hand } from "lucide-react";
import { cn } from "@/lib/utils";

type PermissionMode = "autopilot" | "co_pilot" | "manual";

interface PermissionModeSelectorProps {
  value: PermissionMode;
  onChange: (mode: PermissionMode) => void;
}

const modes = [
  {
    value: "autopilot" as const,
    title: "Autopilot",
    description: "Full automation. AI handles all decisions autonomously.",
    features: [
      "Automatic lead enrichment",
      "AI-generated content",
      "Automatic channel selection",
      "No approval needed",
    ],
    icon: Zap,
    recommended: false,
  },
  {
    value: "co_pilot" as const,
    title: "Co-Pilot",
    description: "AI suggests, you approve key decisions.",
    features: [
      "Automatic lead enrichment",
      "AI-suggested content",
      "Review before sending",
      "Approve high-value actions",
    ],
    icon: Users,
    recommended: true,
  },
  {
    value: "manual" as const,
    title: "Manual",
    description: "Full control. Approve every action.",
    features: [
      "Manual lead review",
      "Review all content",
      "Approve every send",
      "Complete oversight",
    ],
    icon: Hand,
    recommended: false,
  },
];

export function PermissionModeSelector({
  value,
  onChange,
}: PermissionModeSelectorProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {modes.map((mode) => (
        <Card
          key={mode.value}
          className={cn(
            "cursor-pointer transition-all hover:border-primary/50",
            value === mode.value && "border-primary ring-1 ring-primary"
          )}
          onClick={() => onChange(mode.value)}
        >
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <mode.icon className="h-5 w-5 text-muted-foreground" />
                <span className="font-semibold">{mode.title}</span>
              </div>
              {mode.recommended && (
                <Badge variant="secondary" className="text-xs">
                  Recommended
                </Badge>
              )}
            </div>

            <p className="text-sm text-muted-foreground">{mode.description}</p>

            <ul className="space-y-1">
              {mode.features.map((feature) => (
                <li
                  key={feature}
                  className="text-xs text-muted-foreground flex items-center gap-2"
                >
                  <span className="h-1 w-1 rounded-full bg-muted-foreground" />
                  {feature}
                </li>
              ))}
            </ul>

            {value === mode.value && (
              <Badge variant="active" className="w-full justify-center">
                Selected
              </Badge>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
