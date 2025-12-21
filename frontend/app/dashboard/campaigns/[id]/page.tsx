/**
 * FILE: frontend/app/dashboard/campaigns/[id]/page.tsx
 * PURPOSE: Campaign detail page
 * PHASE: 8 (Frontend)
 * TASK: FE-009
 */

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Play, Pause, Settings, Users, Mail, Phone, Linkedin, TrendingUp } from "lucide-react";
import Link from "next/link";

// Placeholder data - would be fetched based on id
const campaign = {
  id: "1",
  name: "Tech Startups Q1 2025",
  status: "active",
  description: "Targeting Series A-B tech startups in Australia with decision makers",
  permissionMode: "co_pilot",
  totalLeads: 450,
  contacted: 234,
  replied: 45,
  converted: 12,
  replyRate: 19.2,
  conversionRate: 5.1,
  allocation: {
    email: 60,
    sms: 20,
    linkedin: 20,
    voice: 0,
    mail: 0,
  },
  targetSettings: {
    industries: ["Technology", "SaaS", "Fintech"],
    titles: ["CEO", "CTO", "Founder", "VP Engineering"],
    companySizes: ["10-50", "51-200"],
    locations: ["Sydney", "Melbourne", "Brisbane"],
  },
  dailyLimit: 50,
  sequenceSteps: 5,
};

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
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
          <p className="text-muted-foreground">{campaign.description}</p>
        </div>
        <div className="flex gap-2">
          {campaign.status === "active" ? (
            <Button variant="outline">
              <Pause className="mr-2 h-4 w-4" />
              Pause
            </Button>
          ) : (
            <Button>
              <Play className="mr-2 h-4 w-4" />
              Activate
            </Button>
          )}
          <Button variant="outline">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Button>
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
            <p className="text-3xl font-bold">{campaign.totalLeads}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Mail className="h-4 w-4" />
              <span className="text-sm">Contacted</span>
            </div>
            <p className="text-3xl font-bold">{campaign.contacted}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <TrendingUp className="h-4 w-4" />
              <span className="text-sm">Reply Rate</span>
            </div>
            <p className="text-3xl font-bold">{campaign.replyRate}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Users className="h-4 w-4" />
              <span className="text-sm">Converted</span>
            </div>
            <p className="text-3xl font-bold">{campaign.converted}</p>
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
            {[
              { channel: "Email", percent: campaign.allocation.email, icon: Mail, color: "bg-blue-500" },
              { channel: "SMS", percent: campaign.allocation.sms, icon: Phone, color: "bg-green-500" },
              { channel: "LinkedIn", percent: campaign.allocation.linkedin, icon: Linkedin, color: "bg-sky-500" },
            ].filter(c => c.percent > 0).map((channel) => (
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
            ))}
          </CardContent>
        </Card>

        {/* Target Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Target Settings</CardTitle>
            <CardDescription>Lead qualification criteria</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-2">Industries</p>
              <div className="flex flex-wrap gap-2">
                {campaign.targetSettings.industries.map((industry) => (
                  <Badge key={industry} variant="secondary">{industry}</Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium mb-2">Job Titles</p>
              <div className="flex flex-wrap gap-2">
                {campaign.targetSettings.titles.map((title) => (
                  <Badge key={title} variant="secondary">{title}</Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium mb-2">Company Sizes</p>
              <div className="flex flex-wrap gap-2">
                {campaign.targetSettings.companySizes.map((size) => (
                  <Badge key={size} variant="secondary">{size} employees</Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium mb-2">Locations</p>
              <div className="flex flex-wrap gap-2">
                {campaign.targetSettings.locations.map((location) => (
                  <Badge key={location} variant="secondary">{location}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Leads */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Campaign Leads</CardTitle>
            <CardDescription>Leads in this campaign</CardDescription>
          </div>
          <Link href={`/dashboard/leads?campaign=${params.id}`}>
            <Button variant="outline">View All Leads</Button>
          </Link>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            Lead list would be displayed here
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
