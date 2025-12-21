/**
 * FILE: frontend/app/dashboard/campaigns/page.tsx
 * PURPOSE: Campaign list page
 * PHASE: 8 (Frontend)
 * TASK: FE-008
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, MoreVertical, Play, Pause, Users, MessageSquare, TrendingUp } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Placeholder data
const campaigns = [
  {
    id: "1",
    name: "Tech Startups Q1 2025",
    status: "active",
    description: "Targeting Series A-B tech startups in Australia",
    totalLeads: 450,
    contacted: 234,
    replied: 45,
    converted: 12,
    replyRate: 19.2,
    conversionRate: 5.1,
    allocation: { email: 60, sms: 20, linkedin: 20 },
  },
  {
    id: "2",
    name: "SaaS Decision Makers",
    status: "active",
    description: "CEOs and CTOs of SaaS companies 10-50 employees",
    totalLeads: 320,
    contacted: 180,
    replied: 28,
    converted: 8,
    replyRate: 15.6,
    conversionRate: 4.4,
    allocation: { email: 50, linkedin: 30, voice: 20 },
  },
  {
    id: "3",
    name: "E-commerce Brands",
    status: "paused",
    description: "D2C brands with $1M+ annual revenue",
    totalLeads: 280,
    contacted: 150,
    replied: 22,
    converted: 5,
    replyRate: 14.7,
    conversionRate: 3.3,
    allocation: { email: 70, sms: 30 },
  },
  {
    id: "4",
    name: "Agency Partnerships",
    status: "draft",
    description: "Marketing agencies looking for white-label services",
    totalLeads: 0,
    contacted: 0,
    replied: 0,
    converted: 0,
    replyRate: 0,
    conversionRate: 0,
    allocation: { email: 100 },
  },
];

export default function CampaignsPage() {
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

      {/* Campaign Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {campaigns.map((campaign) => (
          <Link key={campaign.id} href={`/dashboard/campaigns/${campaign.id}`}>
            <Card className="hover:border-primary/50 transition-colors cursor-pointer">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{campaign.name}</CardTitle>
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
                        <DropdownMenuItem>
                          <Pause className="mr-2 h-4 w-4" />
                          Pause Campaign
                        </DropdownMenuItem>
                      ) : campaign.status !== "draft" ? (
                        <DropdownMenuItem>
                          <Play className="mr-2 h-4 w-4" />
                          Resume Campaign
                        </DropdownMenuItem>
                      ) : (
                        <DropdownMenuItem>
                          <Play className="mr-2 h-4 w-4" />
                          Activate Campaign
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <CardDescription className="line-clamp-1">
                  {campaign.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="flex items-center justify-center gap-1 text-muted-foreground">
                      <Users className="h-3 w-3" />
                      <span className="text-xs">Leads</span>
                    </div>
                    <p className="text-lg font-semibold">{campaign.totalLeads}</p>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-muted-foreground">
                      <MessageSquare className="h-3 w-3" />
                      <span className="text-xs">Replies</span>
                    </div>
                    <p className="text-lg font-semibold">{campaign.replied}</p>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-muted-foreground">
                      <TrendingUp className="h-3 w-3" />
                      <span className="text-xs">Rate</span>
                    </div>
                    <p className="text-lg font-semibold">{campaign.replyRate}%</p>
                  </div>
                </div>

                {/* Channel Allocation Bar */}
                <div className="mt-4">
                  <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
                    {campaign.allocation.email && (
                      <div
                        className="bg-blue-500"
                        style={{ width: `${campaign.allocation.email}%` }}
                      />
                    )}
                    {campaign.allocation.sms && (
                      <div
                        className="bg-green-500"
                        style={{ width: `${campaign.allocation.sms}%` }}
                      />
                    )}
                    {campaign.allocation.linkedin && (
                      <div
                        className="bg-sky-500"
                        style={{ width: `${campaign.allocation.linkedin}%` }}
                      />
                    )}
                    {campaign.allocation.voice && (
                      <div
                        className="bg-purple-500"
                        style={{ width: `${campaign.allocation.voice}%` }}
                      />
                    )}
                  </div>
                  <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                    {campaign.allocation.email && (
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-blue-500" />
                        Email {campaign.allocation.email}%
                      </span>
                    )}
                    {campaign.allocation.sms && (
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-green-500" />
                        SMS {campaign.allocation.sms}%
                      </span>
                    )}
                    {campaign.allocation.linkedin && (
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-sky-500" />
                        LI {campaign.allocation.linkedin}%
                      </span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
