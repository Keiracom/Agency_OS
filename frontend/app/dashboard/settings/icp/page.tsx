/**
 * FILE: frontend/app/dashboard/settings/icp/page.tsx
 * PURPOSE: ICP (Ideal Customer Profile) settings page
 * PHASE: 8 (Frontend)
 * TASK: ICP-007
 */

"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  Building2,
  Users,
  Target,
  Sparkles
} from "lucide-react";
import { useClient } from "@/hooks/use-client";

// Types
interface ICPProfile {
  id: string;
  client_id: string;
  target_industries: string[];
  target_company_sizes: string[];
  target_job_titles: string[];
  target_locations: string[];
  revenue_range_min: number | null;
  revenue_range_max: number | null;
  keywords: string[];
  exclusions: string[];
  pain_points: string[];
  value_propositions: string[];
  extracted_from_website: boolean;
  last_extraction_at: string | null;
  created_at: string;
  updated_at: string;
}

// API functions that take clientId as parameter
async function fetchICP(clientId: string): Promise<ICPProfile> {
  const response = await fetch(`/api/v1/clients/${clientId}/icp`);
  if (!response.ok) {
    throw new Error("Failed to fetch ICP profile");
  }
  return response.json();
}

async function updateICP(clientId: string, data: Partial<ICPProfile>): Promise<ICPProfile> {
  const response = await fetch(`/api/v1/clients/${clientId}/icp`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error("Failed to update ICP profile");
  }
  return response.json();
}

async function reanalyzeWebsite(clientId: string): Promise<{ task_id: string }> {
  const response = await fetch(`/api/v1/clients/${clientId}/icp/reanalyze`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to start website re-analysis");
  }
  return response.json();
}

export default function ICPSettingsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { clientId, isLoading: clientLoading } = useClient();

  // Form state
  const [industries, setIndustries] = useState("");
  const [companySizes, setCompanySizes] = useState("");
  const [jobTitles, setJobTitles] = useState("");
  const [locations, setLocations] = useState("");
  const [revenueMin, setRevenueMin] = useState("");
  const [revenueMax, setRevenueMax] = useState("");
  const [keywords, setKeywords] = useState("");
  const [exclusions, setExclusions] = useState("");
  const [painPoints, setPainPoints] = useState("");
  const [valueProps, setValueProps] = useState("");

  // Fetch ICP data (enabled only when clientId is available)
  const { data: icp, isLoading, error } = useQuery({
    queryKey: ["icp", clientId],
    queryFn: () => fetchICP(clientId!),
    enabled: !!clientId,
  });

  // Update form when data loads
  useEffect(() => {
    if (icp) {
      setIndustries(icp.target_industries?.join(", ") || "");
      setCompanySizes(icp.target_company_sizes?.join(", ") || "");
      setJobTitles(icp.target_job_titles?.join(", ") || "");
      setLocations(icp.target_locations?.join(", ") || "");
      setRevenueMin(icp.revenue_range_min?.toString() || "");
      setRevenueMax(icp.revenue_range_max?.toString() || "");
      setKeywords(icp.keywords?.join(", ") || "");
      setExclusions(icp.exclusions?.join(", ") || "");
      setPainPoints(icp.pain_points?.join("\n") || "");
      setValueProps(icp.value_propositions?.join("\n") || "");
    }
  }, [icp]);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<ICPProfile>) => updateICP(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["icp", clientId] });
      toast({
        title: "ICP Updated",
        description: "Your Ideal Customer Profile has been saved successfully.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to update ICP profile",
        variant: "destructive",
      });
    },
  });

  // Re-analyze mutation
  const reanalyzeMutation = useMutation({
    mutationFn: () => reanalyzeWebsite(clientId!),
    onSuccess: () => {
      toast({
        title: "Re-analysis Started",
        description: "We're analyzing your website again. This may take a few minutes.",
      });
      // Could poll for status using task_id from response
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to start website re-analysis",
        variant: "destructive",
      });
    },
  });

  // Parse comma-separated values to array
  const parseList = (value: string): string[] => {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  };

  // Parse newline-separated values to array
  const parseLines = (value: string): string[] => {
    return value
      .split("\n")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    updateMutation.mutate({
      target_industries: parseList(industries),
      target_company_sizes: parseList(companySizes),
      target_job_titles: parseList(jobTitles),
      target_locations: parseList(locations),
      revenue_range_min: revenueMin ? parseInt(revenueMin) : null,
      revenue_range_max: revenueMax ? parseInt(revenueMax) : null,
      keywords: parseList(keywords),
      exclusions: parseList(exclusions),
      pain_points: parseLines(painPoints),
      value_propositions: parseLines(valueProps),
    });
  };

  // Show loading state while client context loads
  if (clientLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Show error if no client found
  if (!clientId) {
    return (
      <div className="space-y-6 max-w-4xl">
        <Link href="/dashboard/settings">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Settings
          </Button>
        </Link>
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">Unable to load client context. Please try again.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 max-w-4xl">
        <Link href="/dashboard/settings">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Settings
          </Button>
        </Link>
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">Error loading ICP profile. Please try again.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back Button */}
      <Link href="/dashboard/settings">
        <Button variant="ghost" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Settings
        </Button>
      </Link>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ideal Customer Profile</h1>
          <p className="text-muted-foreground">
            Define who you want to reach. This profile is used across all your campaigns.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => reanalyzeMutation.mutate()}
          disabled={reanalyzeMutation.isPending}
        >
          {reanalyzeMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Re-analyze Website
        </Button>
      </div>

      {/* Extraction Status */}
      {icp?.extracted_from_website && (
        <Card className="bg-muted/50">
          <CardContent className="p-4 flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-primary" />
            <div>
              <p className="text-sm font-medium">AI-Extracted Profile</p>
              <p className="text-xs text-muted-foreground">
                Last extracted from your website on{" "}
                {icp.last_extraction_at
                  ? new Date(icp.last_extraction_at).toLocaleDateString()
                  : "N/A"}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Target Companies */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-muted-foreground" />
                <CardTitle>Target Companies</CardTitle>
              </div>
              <CardDescription>Define the types of companies you want to reach</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="industries">Industries</Label>
                <Input
                  id="industries"
                  placeholder="e.g., Technology, SaaS, Fintech, Healthcare"
                  value={industries}
                  onChange={(e) => setIndustries(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Comma-separated list of target industries</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="companySizes">Company Sizes</Label>
                  <Input
                    id="companySizes"
                    placeholder="e.g., 10-50, 51-200, 201-500"
                    value={companySizes}
                    onChange={(e) => setCompanySizes(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="locations">Locations</Label>
                  <Input
                    id="locations"
                    placeholder="e.g., Sydney, Melbourne, Brisbane"
                    value={locations}
                    onChange={(e) => setLocations(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="revenueMin">Revenue Min ($)</Label>
                  <Input
                    id="revenueMin"
                    type="number"
                    placeholder="e.g., 1000000"
                    value={revenueMin}
                    onChange={(e) => setRevenueMin(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="revenueMax">Revenue Max ($)</Label>
                  <Input
                    id="revenueMax"
                    type="number"
                    placeholder="e.g., 50000000"
                    value={revenueMax}
                    onChange={(e) => setRevenueMax(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Target Contacts */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-muted-foreground" />
                <CardTitle>Target Contacts</CardTitle>
              </div>
              <CardDescription>Define the roles you want to reach</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="jobTitles">Job Titles</Label>
                <Input
                  id="jobTitles"
                  placeholder="e.g., CEO, CTO, VP Engineering, Founder"
                  value={jobTitles}
                  onChange={(e) => setJobTitles(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Comma-separated list of target job titles</p>
              </div>
            </CardContent>
          </Card>

          {/* Keywords & Exclusions */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Target className="h-5 w-5 text-muted-foreground" />
                <CardTitle>Keywords & Exclusions</CardTitle>
              </div>
              <CardDescription>Refine your targeting with keywords</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="keywords">Include Keywords</Label>
                <Input
                  id="keywords"
                  placeholder="e.g., AI, machine learning, automation, B2B"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Look for these keywords in company descriptions</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="exclusions">Exclude Keywords</Label>
                <Input
                  id="exclusions"
                  placeholder="e.g., agency, consulting, freelance"
                  value={exclusions}
                  onChange={(e) => setExclusions(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Skip companies with these keywords</p>
              </div>
            </CardContent>
          </Card>

          {/* Messaging */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-muted-foreground" />
                <CardTitle>Messaging Context</CardTitle>
              </div>
              <CardDescription>Help the AI craft better messages</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="painPoints">Pain Points</Label>
                <Textarea
                  id="painPoints"
                  placeholder="Enter each pain point on a new line..."
                  value={painPoints}
                  onChange={(e) => setPainPoints(e.target.value)}
                  rows={4}
                />
                <p className="text-xs text-muted-foreground">Problems your ideal customers face (one per line)</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="valueProps">Value Propositions</Label>
                <Textarea
                  id="valueProps"
                  placeholder="Enter each value proposition on a new line..."
                  value={valueProps}
                  onChange={(e) => setValueProps(e.target.value)}
                  rows={4}
                />
                <p className="text-xs text-muted-foreground">How you solve their problems (one per line)</p>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex gap-4">
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
            <Link href="/dashboard/settings">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
          </div>
        </form>
      )}
    </div>
  );
}

// === VERIFICATION CHECKLIST ===
// [x] Contract comment at top
// [x] Uses React Query for API calls
// [x] Shows toast on error
// [x] All fields editable
// [x] Re-analyze Website button
// [x] Save changes → PUT endpoint
// [x] Navigation link back to settings
