/**
 * FILE: frontend/app/dashboard/leads/[id]/page.tsx
 * PURPOSE: Lead detail page with ALS scoring breakdown
 * PHASE: 8 (Frontend)
 * TASK: FE-012
 */

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Mail, Phone, Linkedin, Building2, MapPin, Globe, Calendar, TrendingUp } from "lucide-react";
import Link from "next/link";
import { getTierColor } from "@/lib/utils";

// Placeholder data - would be fetched based on id
const lead = {
  id: "1",
  firstName: "Sarah",
  lastName: "Chen",
  email: "sarah.chen@techvision.io",
  phone: "+61 412 345 678",
  linkedinUrl: "https://linkedin.com/in/sarahchen",
  title: "Chief Technology Officer",
  company: {
    name: "TechVision AI",
    domain: "techvision.io",
    industry: "Artificial Intelligence",
    size: "51-200",
    location: "Sydney, Australia",
    founded: 2019,
    funding: "Series A",
  },
  als: {
    total: 87,
    tier: "hot",
    components: {
      dataQuality: 92,
      authority: 95,
      companyFit: 85,
      timing: 78,
      risk: 85,
    },
  },
  campaign: {
    id: "1",
    name: "Tech Startups Q1 2025",
  },
  status: "contacted",
  sequenceStep: 2,
  lastActivity: "2025-01-18T14:30:00Z",
  createdAt: "2025-01-10T09:00:00Z",
  timeline: [
    { date: "2025-01-18T14:30:00Z", action: "Email opened", channel: "email" },
    { date: "2025-01-17T10:00:00Z", action: "Email sent (Step 2)", channel: "email" },
    { date: "2025-01-15T09:00:00Z", action: "Email opened", channel: "email" },
    { date: "2025-01-14T11:00:00Z", action: "Email sent (Step 1)", channel: "email" },
    { date: "2025-01-10T09:00:00Z", action: "Lead created", channel: "system" },
  ],
};

const alsLabels: Record<string, string> = {
  dataQuality: "Data Quality",
  authority: "Authority",
  companyFit: "Company Fit",
  timing: "Timing",
  risk: "Risk",
};

const alsDescriptions: Record<string, string> = {
  dataQuality: "Completeness and accuracy of lead data",
  authority: "Decision-making power and seniority",
  companyFit: "Match with ideal customer profile",
  timing: "Buying signals and readiness",
  risk: "Deliverability and compliance risk",
};

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  const tierColor = getTierColor(lead.als.tier);

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link href="/dashboard/leads">
        <Button variant="ghost" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Leads
        </Button>
      </Link>

      {/* Lead Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">
              {lead.firstName} {lead.lastName}
            </h1>
            <Badge className={tierColor}>
              ALS: {lead.als.total}
            </Badge>
            <Badge variant="secondary" className="capitalize">
              {lead.status}
            </Badge>
          </div>
          <p className="text-lg text-muted-foreground">
            {lead.title} at {lead.company.name}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Mail className="mr-2 h-4 w-4" />
            Send Email
          </Button>
          <Button>
            <TrendingUp className="mr-2 h-4 w-4" />
            Re-score
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Contact Info */}
        <Card>
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <a href={`mailto:${lead.email}`} className="text-sm hover:underline">
                {lead.email}
              </a>
            </div>
            {lead.phone && (
              <div className="flex items-center gap-3">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <a href={`tel:${lead.phone}`} className="text-sm hover:underline">
                  {lead.phone}
                </a>
              </div>
            )}
            {lead.linkedinUrl && (
              <div className="flex items-center gap-3">
                <Linkedin className="h-4 w-4 text-muted-foreground" />
                <a
                  href={lead.linkedinUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm hover:underline"
                >
                  LinkedIn Profile
                </a>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Company Info */}
        <Card>
          <CardHeader>
            <CardTitle>Company</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{lead.company.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <a
                href={`https://${lead.company.domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm hover:underline"
              >
                {lead.company.domain}
              </a>
            </div>
            <div className="flex items-center gap-3">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">{lead.company.location}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2 border-t">
              <div>
                <p className="text-xs text-muted-foreground">Industry</p>
                <p className="text-sm font-medium">{lead.company.industry}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Size</p>
                <p className="text-sm font-medium">{lead.company.size}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Founded</p>
                <p className="text-sm font-medium">{lead.company.founded}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Funding</p>
                <p className="text-sm font-medium">{lead.company.funding}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Campaign Info */}
        <Card>
          <CardHeader>
            <CardTitle>Campaign</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link
              href={`/dashboard/campaigns/${lead.campaign.id}`}
              className="text-sm font-medium hover:underline"
            >
              {lead.campaign.name}
            </Link>
            <div className="grid grid-cols-2 gap-2 pt-2 border-t">
              <div>
                <p className="text-xs text-muted-foreground">Sequence Step</p>
                <p className="text-sm font-medium">{lead.sequenceStep} of 5</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <Badge variant="secondary" className="capitalize">
                  {lead.status}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ALS Score Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>ALS Score Breakdown</CardTitle>
          <CardDescription>
            Agency OS Lead Score - 5 component scoring system
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-6">
            <div className={`text-5xl font-bold ${tierColor.replace("bg-", "text-").replace("-500", "-600")}`}>
              {lead.als.total}
            </div>
            <div>
              <Badge className={`${tierColor} capitalize text-base px-3 py-1`}>
                {lead.als.tier} Lead
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">
                Top 15% of leads in this campaign
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-5">
            {Object.entries(lead.als.components).map(([key, value]) => (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{alsLabels[key]}</span>
                  <span className="text-sm font-bold">{value}</span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted">
                  <div
                    className={`h-2 rounded-full ${
                      value >= 85 ? "bg-green-500" :
                      value >= 60 ? "bg-yellow-500" :
                      value >= 35 ? "bg-orange-500" : "bg-red-500"
                    }`}
                    style={{ width: `${value}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">{alsDescriptions[key]}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Activity Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Timeline</CardTitle>
          <CardDescription>Recent interactions with this lead</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {lead.timeline.map((event, index) => (
              <div key={index} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className={`h-3 w-3 rounded-full ${
                    event.channel === "email" ? "bg-blue-500" :
                    event.channel === "sms" ? "bg-green-500" :
                    event.channel === "linkedin" ? "bg-sky-500" :
                    "bg-gray-500"
                  }`} />
                  {index < lead.timeline.length - 1 && (
                    <div className="w-0.5 h-full bg-muted my-1" />
                  )}
                </div>
                <div className="flex-1 pb-4">
                  <p className="text-sm font-medium">{event.action}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(event.date).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
