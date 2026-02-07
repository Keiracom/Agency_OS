/**
 * FILE: frontend/app/dashboard/campaigns/[id]/page.tsx
 * PURPOSE: Campaign detail page with real API data
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006 (P0 Dashboard Wiring)
 */

"use client";

import { use } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  Play,
  Pause,
  Settings,
  Users,
  Mail,
  Phone,
  Linkedin,
  TrendingUp,
  Calendar,
  Target,
  AlertCircle,
} from "lucide-react";
import { useCampaign, useActivateCampaign, usePauseCampaign } from "@/hooks/use-campaigns";
import { useToast } from "@/hooks/use-toast";
import { ErrorState } from "@/components/ui/error-state";
import type { Campaign } from "@/lib/api/types";

// Loading skeleton component
function CampaignDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Skeleton className="h-10 w-40" />

      {/* Campaign Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-10 w-80" />
          <Skeleton className="h-5 w-96" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <Skeleton className="h-4 w-20 mb-2" />
              <Skeleton className="h-9 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Cards */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-60" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-60" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Campaign content component
function CampaignDetailContent({ campaign }: { campaign: Campaign }) {
  const { toast } = useToast();
  const activateMutation = useActivateCampaign();
  const pauseMutation = usePauseCampaign();

  const handleActivate = async () => {
    try {
      await activateMutation.mutateAsync(campaign.id);
      toast({ title: "Campaign activated" });
    } catch {
      toast({ title: "Failed to activate campaign", variant: "destructive" });
    }
  };

  const handlePause = async () => {
    try {
      await pauseMutation.mutateAsync(campaign.id);
      toast({ title: "Campaign paused" });
    } catch {
      toast({ title: "Failed to pause campaign", variant: "destructive" });
    }
  };

  // Calculate channel allocations
  const channelAllocations = [
    { channel: "Email", percent: campaign.allocation_email, icon: Mail, color: "bg-blue-500" },
    { channel: "SMS", percent: campaign.allocation_sms, icon: Phone, color: "bg-green-500" },
    { channel: "LinkedIn", percent: campaign.allocation_linkedin, icon: Linkedin, color: "bg-sky-500" },
    { channel: "Voice", percent: campaign.allocation_voice, icon: Phone, color: "bg-purple-500" },
    { channel: "Mail", percent: campaign.allocation_mail, icon: Mail, color: "bg-amber-500" },
  ].filter(c => c.percent > 0);

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link href="/dashboard/campaigns">
        <Button variant="ghost" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </Button>
      </Link>

      {/* Campaign Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{campaign.name}</h1>
            <Badge variant={campaign.status as "active" | "paused" | "draft"} className="capitalize">
              {campaign.status}
            </Badge>
          </div>
          {campaign.description && (
            <p className="text-muted-foreground">{campaign.description}</p>
          )}
          {campaign.permission_mode && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target className="h-4 w-4" />
              <span className="capitalize">{campaign.permission_mode.replace("_", " ")} mode</span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {campaign.status === "active" ? (
            <Button 
              variant="outline" 
              onClick={handlePause}
              disabled={pauseMutation.isPending}
            >
              <Pause className="mr-2 h-4 w-4" />
              {pauseMutation.isPending ? "Pausing..." : "Pause"}
            </Button>
          ) : campaign.status !== "completed" ? (
            <Button 
              onClick={handleActivate}
              disabled={activateMutation.isPending}
            >
              <Play className="mr-2 h-4 w-4" />
              {activateMutation.isPending ? "Activating..." : campaign.status === "draft" ? "Activate" : "Resume"}
            </Button>
          ) : null}
          <Link href={`/dashboard/campaigns/${campaign.id}/settings`}>
            <Button variant="outline">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Users className="h-4 w-4" />
              <span className="text-sm">Total Leads</span>
            </div>
            <p className="text-3xl font-bold">{campaign.total_leads.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Mail className="h-4 w-4" />
              <span className="text-sm">Contacted</span>
            </div>
            <p className="text-3xl font-bold">{campaign.leads_contacted.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <TrendingUp className="h-4 w-4" />
              <span className="text-sm">Reply Rate</span>
            </div>
            <p className="text-3xl font-bold">{campaign.reply_rate.toFixed(1)}%</p>
            <p className="text-xs text-muted-foreground mt-1">
              {campaign.leads_replied.toLocaleString()} replies
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Calendar className="h-4 w-4" />
              <span className="text-sm">Meetings Booked</span>
            </div>
            <p className="text-3xl font-bold">{campaign.meetings_booked}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {campaign.show_rate.toFixed(0)}% show rate
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Secondary Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Target className="h-4 w-4" />
              <span className="text-sm">Conversion Rate</span>
            </div>
            <p className="text-2xl font-bold">{campaign.conversion_rate.toFixed(1)}%</p>
            <p className="text-xs text-muted-foreground mt-1">
              {campaign.leads_converted.toLocaleString()} converted
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Mail className="h-4 w-4" />
              <span className="text-sm">Active Sequences</span>
            </div>
            <p className="text-2xl font-bold">{campaign.active_sequences}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Target className="h-4 w-4" />
              <span className="text-sm">Lead Allocation</span>
            </div>
            <p className="text-2xl font-bold">{campaign.lead_allocation_pct}%</p>
            <p className="text-xs text-muted-foreground mt-1">
              of lead pool priority
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Channel Allocation */}
        <Card>
          <CardHeader>
            <CardTitle>Channel Allocation</CardTitle>
            <CardDescription>Distribution of outreach across channels</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {channelAllocations.length > 0 ? (
              channelAllocations.map((channel) => (
                <div key={channel.channel} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <channel.icon className="h-4 w-4 text-muted-foreground" />
                      <span>{channel.channel}</span>
                    </div>
                    <span className="font-medium">{channel.percent}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted">
                    <div
                      className={`h-2 rounded-full ${channel.color}`}
                      style={{ width: `${channel.percent}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground text-center py-4">
                No channel allocation configured
              </p>
            )}
          </CardContent>
        </Card>

        {/* Campaign Info */}
        <Card>
          <CardHeader>
            <CardTitle>Campaign Details</CardTitle>
            <CardDescription>Configuration and schedule</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm text-muted-foreground">Daily Limit</span>
              <span className="font-medium">{campaign.daily_limit} leads/day</span>
            </div>
            {campaign.start_date && (
              <div className="flex justify-between items-center py-2 border-b">
                <span className="text-sm text-muted-foreground">Start Date</span>
                <span className="font-medium">
                  {new Date(campaign.start_date).toLocaleDateString()}
                </span>
              </div>
            )}
            {campaign.end_date && (
              <div className="flex justify-between items-center py-2 border-b">
                <span className="text-sm text-muted-foreground">End Date</span>
                <span className="font-medium">
                  {new Date(campaign.end_date).toLocaleDateString()}
                </span>
              </div>
            )}
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm text-muted-foreground">Permission Mode</span>
              <Badge variant="secondary" className="capitalize">
                {campaign.permission_mode?.replace("_", " ") || "Default"}
              </Badge>
            </div>
            {campaign.is_ai_suggested && (
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-muted-foreground">AI Suggested</span>
                <Badge variant="secondary">Yes</Badge>
              </div>
            )}
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-muted-foreground">Created</span>
              <span className="text-sm">
                {new Date(campaign.created_at).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Campaign Leads Link */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Campaign Leads</CardTitle>
            <CardDescription>
              {campaign.total_leads.toLocaleString()} leads in this campaign
            </CardDescription>
          </div>
          <Link href={`/dashboard/leads?campaign=${campaign.id}`}>
            <Button variant="outline">View All Leads</Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 text-center py-4">
            <div>
              <p className="text-2xl font-bold text-muted-foreground">
                {campaign.total_leads.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-500">
                {campaign.leads_contacted.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">Contacted</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-500">
                {campaign.leads_replied.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">Replied</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-500">
                {campaign.leads_converted.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">Converted</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Main page component
export default function CampaignDetailPage({ 
  params 
}: { 
  params: Promise<{ id: string }> 
}) {
  const resolvedParams = use(params);
  const { data: campaign, isLoading, error, refetch } = useCampaign(resolvedParams.id);

  if (isLoading) {
    return <CampaignDetailSkeleton />;
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link href="/dashboard/campaigns">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Campaigns
          </Button>
        </Link>
        <ErrorState 
          error={error} 
          onRetry={refetch} 
          title="Failed to load campaign"
        />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="space-y-6">
        <Link href="/dashboard/campaigns">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Campaigns
          </Button>
        </Link>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">Campaign Not Found</h3>
            <p className="text-muted-foreground mt-1">
              The campaign you&apos;re looking for doesn&apos;t exist or has been deleted.
            </p>
            <Link href="/dashboard/campaigns" className="mt-4">
              <Button>Back to Campaigns</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <CampaignDetailContent campaign={campaign} />;
}
