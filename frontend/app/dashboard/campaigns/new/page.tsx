/**
 * FILE: frontend/app/dashboard/campaigns/new/page.tsx
 * PURPOSE: New campaign creation page (simplified - ICP-008)
 * PHASE: 8 (Frontend)
 * TASK: ICP-008
 * UPDATED: E2E Fix - Use proper useClient hook and authenticated API calls
 *
 * CHANGES:
 * - Removed channel allocation fields (system handles based on ALS)
 * - Removed targeting fields (inherited from client ICP)
 * - Removed scheduling fields
 * - Added inherited ICP display
 * - Added link to ICP settings
 * - Fixed: Use useClient hook instead of hardcoded mock ID
 * - Fixed: Use proper API client with authentication
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Loader2, Target, Settings, Sparkles, AlertCircle } from "lucide-react";
import { PermissionModeSelector } from "@/components/campaigns/permission-mode-selector";
import { useToast } from "@/hooks/use-toast";
import { useClient } from "@/hooks/use-client";
import { useCreateCampaign } from "@/hooks/use-campaigns";
import { api } from "@/lib/api";

// Types
interface ICPProfile {
  icp_industries: string[];
  icp_company_sizes: string[];
  icp_titles: string[];
  icp_locations: string[];
}

export default function NewCampaignPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [permissionMode, setPermissionMode] = useState<"autopilot" | "co_pilot" | "manual">("co_pilot");

  const router = useRouter();
  const { toast } = useToast();
  const { clientId, isLoading: clientLoading } = useClient();

  // Fetch ICP to display inherited targeting
  const { data: icp, isLoading: icpLoading } = useQuery({
    queryKey: ["icp", clientId],
    queryFn: async (): Promise<ICPProfile> => {
      if (!clientId) {
        return { icp_industries: [], icp_company_sizes: [], icp_titles: [], icp_locations: [] };
      }
      try {
        const response = await api.get<ICPProfile>(`/api/v1/clients/${clientId}/icp`);
        return response;
      } catch {
        // Return empty ICP if not found
        return { icp_industries: [], icp_company_sizes: [], icp_titles: [], icp_locations: [] };
      }
    },
    enabled: !!clientId,
  });

  // Create campaign mutation using the proper hook
  const createMutation = useCreateCampaign();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a campaign name",
        variant: "destructive",
      });
      return;
    }

    if (!clientId) {
      toast({
        title: "Error",
        description: "Client context not loaded. Please refresh the page.",
        variant: "destructive",
      });
      return;
    }

    createMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      permission_mode: permissionMode,
    }, {
      onSuccess: () => {
        toast({
          title: "Campaign created",
          description: "Your campaign has been created successfully",
        });
        router.push("/dashboard/campaigns");
      },
      onError: (error: Error) => {
        toast({
          title: "Error",
          description: error.message || "Failed to create campaign",
          variant: "destructive",
        });
      },
    });
  };

  // Check if ICP has any targeting configured
  const hasICP = icp && (
    (icp.icp_industries?.length ?? 0) > 0 ||
    (icp.icp_locations?.length ?? 0) > 0 ||
    (icp.icp_titles?.length ?? 0) > 0
  );

  // Show loading state while client context is loading
  if (clientLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Show error if no client context
  if (!clientId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">Unable to load client context</p>
        <Button onClick={() => router.push("/login")}>Return to Login</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back Button */}
      <Link href="/dashboard/campaigns">
        <Button variant="ghost" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </Button>
      </Link>

      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create Campaign</h1>
        <p className="text-muted-foreground">
          Set up a new outreach campaign
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Campaign Details</CardTitle>
            <CardDescription>Name and describe your campaign</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Tech Startups Q1 2025"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                placeholder="Brief description of your campaign goals"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Inherited ICP Display */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Target className="h-5 w-5 text-muted-foreground" />
              <CardTitle>Targeting</CardTitle>
            </div>
            <CardDescription>
              This campaign will use your organization's Ideal Customer Profile
            </CardDescription>
          </CardHeader>
          <CardContent>
            {icpLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading ICP...
              </div>
            ) : hasICP ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {(icp?.icp_industries ?? []).slice(0, 5).map((industry) => (
                    <Badge key={industry} variant="secondary">
                      {industry}
                    </Badge>
                  ))}
                  {(icp?.icp_industries?.length ?? 0) > 5 && (
                    <Badge variant="outline">+{(icp?.icp_industries?.length ?? 0) - 5} more</Badge>
                  )}
                </div>
                {(icp?.icp_locations?.length ?? 0) > 0 && (
                  <p className="text-sm text-muted-foreground">
                    Locations: {(icp?.icp_locations ?? []).join(", ")}
                  </p>
                )}
                {(icp?.icp_titles?.length ?? 0) > 0 && (
                  <p className="text-sm text-muted-foreground">
                    Titles: {(icp?.icp_titles ?? []).slice(0, 5).join(", ")}
                    {(icp?.icp_titles?.length ?? 0) > 5 && ` +${(icp?.icp_titles?.length ?? 0) - 5} more`}
                  </p>
                )}
                <Link
                  href="/dashboard/settings/icp"
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <Settings className="h-3 w-3" />
                  Edit targeting
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  No Ideal Customer Profile configured yet. Set up your ICP to define who you want to reach.
                </p>
                <Link href="/dashboard/settings/icp">
                  <Button variant="outline" size="sm">
                    <Target className="mr-2 h-4 w-4" />
                    Configure ICP
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Channel Allocation Info */}
        <Card className="bg-muted/30">
          <CardContent className="p-4 flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-primary mt-0.5" />
            <div>
              <p className="text-sm font-medium">Smart Channel Allocation</p>
              <p className="text-xs text-muted-foreground mt-1">
                The system automatically determines the best channels (Email, SMS, LinkedIn, Voice)
                for each lead based on their ALS score and engagement history.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Permission Mode */}
        <Card>
          <CardHeader>
            <CardTitle>Permission Mode</CardTitle>
            <CardDescription>Choose your automation level</CardDescription>
          </CardHeader>
          <CardContent>
            <PermissionModeSelector
              value={permissionMode}
              onChange={setPermissionMode}
            />
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex gap-4">
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Campaign"
            )}
          </Button>
          <Link href="/dashboard/campaigns">
            <Button type="button" variant="outline">Cancel</Button>
          </Link>
        </div>
      </form>
    </div>
  );
}

// === VERIFICATION CHECKLIST ===
// [x] Removed channel allocation fields
// [x] Removed targeting fields (industries, titles, etc.)
// [x] Removed scheduling/daily limit fields
// [x] Kept: Campaign name, Description (optional), Permission mode
// [x] Added: Display inherited ICP
// [x] Added: Link to ICP settings ("Edit targeting")
// [x] Uses React Query for API calls
// [x] Shows toast on error
