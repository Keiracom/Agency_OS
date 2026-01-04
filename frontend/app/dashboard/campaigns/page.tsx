/**
 * FILE: frontend/app/dashboard/campaigns/page.tsx
 * PURPOSE: Campaign list page with real data
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Plus, MoreVertical, Play, Pause, Users, MessageSquare, TrendingUp, Search } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCampaigns, useActivateCampaign, usePauseCampaign } from "@/hooks/use-campaigns";
import { CardListSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { NoItemsState, NoSearchResults } from "@/components/ui/empty-state";
import { useToast } from "@/hooks/use-toast";
import type { Campaign, CampaignStatus } from "@/lib/api/types";

export default function CampaignsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | undefined>();
  const { toast } = useToast();

  const { data, isLoading, error, refetch } = useCampaigns({
    search: search || undefined,
    status: statusFilter,
  });

  const activateMutation = useActivateCampaign();
  const pauseMutation = usePauseCampaign();

  const handleActivate = async (campaignId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await activateMutation.mutateAsync(campaignId);
      toast({ title: "Campaign activated" });
    } catch {
      toast({ title: "Failed to activate campaign", variant: "destructive" });
    }
  };

  const handlePause = async (campaignId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await pauseMutation.mutateAsync(campaignId);
      toast({ title: "Campaign paused" });
    } catch {
      toast({ title: "Failed to pause campaign", variant: "destructive" });
    }
  };

  const campaigns = data?.items || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Campaigns</h1>
          <p className="text-muted-foreground">
            Manage your outreach campaigns and track performance
          </p>
        </div>
        <Link href="/dashboard/campaigns/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Search */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search campaigns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          {(["active", "paused", "draft", "completed"] as CampaignStatus[]).map((status) => (
            <Button
              key={status}
              variant={statusFilter === status ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(statusFilter === status ? undefined : status)}
              className="capitalize"
            >
              {status}
            </Button>
          ))}
        </div>
      </div>

      {/* Campaign Grid */}
      {isLoading ? (
        <CardListSkeleton count={6} />
      ) : error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : campaigns.length === 0 ? (
        search ? (
          <NoSearchResults query={search} onClear={() => setSearch("")} />
        ) : (
          <NoItemsState
            itemName="Campaign"
            onCreate={() => (window.location.href = "/dashboard/campaigns/new")}
          />
        )
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {campaigns.map((campaign: Campaign) => (
            <Link key={campaign.id} href={`/dashboard/campaigns/${campaign.id}`}>
              <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg line-clamp-1">{campaign.name}</CardTitle>
                      <Badge
                        variant={campaign.status as "active" | "paused" | "draft"}
                        className="capitalize"
                      >
                        {campaign.status}
                      </Badge>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.preventDefault()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {campaign.status === "active" ? (
                          <DropdownMenuItem onClick={(e) => handlePause(campaign.id, e)}>
                            <Pause className="mr-2 h-4 w-4" />
                            Pause Campaign
                          </DropdownMenuItem>
                        ) : campaign.status !== "completed" ? (
                          <DropdownMenuItem onClick={(e) => handleActivate(campaign.id, e)}>
                            <Play className="mr-2 h-4 w-4" />
                            {campaign.status === "draft" ? "Activate" : "Resume"} Campaign
                          </DropdownMenuItem>
                        ) : null}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  {campaign.description && (
                    <CardDescription className="line-clamp-1">
                      {campaign.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="flex items-center justify-center gap-1 text-muted-foreground">
                        <Users className="h-3 w-3" />
                        <span className="text-xs">Leads</span>
                      </div>
                      <p className="text-lg font-semibold">{campaign.total_leads}</p>
                    </div>
                    <div>
                      <div className="flex items-center justify-center gap-1 text-muted-foreground">
                        <MessageSquare className="h-3 w-3" />
                        <span className="text-xs">Replies</span>
                      </div>
                      <p className="text-lg font-semibold">{campaign.leads_replied}</p>
                    </div>
                    <div>
                      <div className="flex items-center justify-center gap-1 text-muted-foreground">
                        <TrendingUp className="h-3 w-3" />
                        <span className="text-xs">Rate</span>
                      </div>
                      <p className="text-lg font-semibold">{campaign.reply_rate.toFixed(1)}%</p>
                    </div>
                  </div>

                  {/* Channel Allocation Bar */}
                  <div className="mt-4">
                    <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
                      {campaign.allocation_email > 0 && (
                        <div
                          className="bg-blue-500"
                          style={{ width: `${campaign.allocation_email}%` }}
                        />
                      )}
                      {campaign.allocation_sms > 0 && (
                        <div
                          className="bg-green-500"
                          style={{ width: `${campaign.allocation_sms}%` }}
                        />
                      )}
                      {campaign.allocation_linkedin > 0 && (
                        <div
                          className="bg-sky-500"
                          style={{ width: `${campaign.allocation_linkedin}%` }}
                        />
                      )}
                      {campaign.allocation_voice > 0 && (
                        <div
                          className="bg-purple-500"
                          style={{ width: `${campaign.allocation_voice}%` }}
                        />
                      )}
                      {campaign.allocation_mail > 0 && (
                        <div
                          className="bg-amber-500"
                          style={{ width: `${campaign.allocation_mail}%` }}
                        />
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      {campaign.allocation_email > 0 && (
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-blue-500" />
                          Email {campaign.allocation_email}%
                        </span>
                      )}
                      {campaign.allocation_sms > 0 && (
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-green-500" />
                          SMS {campaign.allocation_sms}%
                        </span>
                      )}
                      {campaign.allocation_linkedin > 0 && (
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-sky-500" />
                          LI {campaign.allocation_linkedin}%
                        </span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
