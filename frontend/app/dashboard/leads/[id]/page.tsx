/**
 * FILE: frontend/app/dashboard/leads/[id]/page.tsx
 * PURPOSE: Lead detail page with ALS scoring breakdown and activity timeline with content visibility
 * PHASE: 14 (Missing UI)
 * TASK: MUI-004 (Content visibility in timeline)
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Mail,
  Phone,
  Linkedin,
  Building2,
  MapPin,
  Globe,
  TrendingUp,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  MessageSquare,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useLead, useLeadActivities } from "@/hooks/use-leads";
import { DetailPageSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/hooks/use-toast";
import { getTierColor } from "@/lib/utils";

const alsLabels: Record<string, string> = {
  data_quality: "Data Quality",
  authority: "Authority",
  company_fit: "Company Fit",
  timing: "Timing",
  risk: "Risk",
};

const alsDescriptions: Record<string, string> = {
  data_quality: "Completeness and accuracy of lead data",
  authority: "Decision-making power and seniority",
  company_fit: "Match with ideal customer profile",
  timing: "Buying signals and readiness",
  risk: "Deliverability and compliance risk",
};

function ActivityTimelineItem({
  activity,
  isLast,
}: {
  activity: {
    id: string;
    channel: string;
    action: string;
    sequence_step?: number | null;
    subject?: string | null;
    content_preview?: string | null;
    created_at: string;
    intent?: string | null;
  };
  isLast: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const hasContent = activity.content_preview && activity.content_preview.length > 0;
  const isSent = activity.action.includes("sent");
  const isReceived = activity.action.includes("replied") || activity.action.includes("received");

  const handleCopy = async () => {
    if (activity.content_preview) {
      await navigator.clipboard.writeText(activity.content_preview);
      setCopied(true);
      toast({ title: "Copied to clipboard" });
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const channelColors: Record<string, string> = {
    email: "bg-blue-500",
    sms: "bg-green-500",
    linkedin: "bg-sky-500",
    voice: "bg-purple-500",
    mail: "bg-amber-500",
    system: "bg-gray-500",
  };

  return (
    <div className="flex gap-4">
      {/* Timeline indicator */}
      <div className="flex flex-col items-center">
        <div
          className={`h-3 w-3 rounded-full ${channelColors[activity.channel] || "bg-gray-500"}`}
        />
        {!isLast && <div className="w-0.5 flex-1 bg-muted my-1" />}
      </div>

      {/* Content */}
      <div className={`flex-1 pb-4 ${isReceived ? "pl-0" : ""}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium">{activity.action}</p>
            <p className="text-xs text-muted-foreground">
              {new Date(activity.created_at).toLocaleString()}
            </p>
          </div>
          {activity.intent && (
            <Badge variant="outline" className="capitalize text-xs">
              {activity.intent.replace("_", " ")}
            </Badge>
          )}
        </div>

        {/* Subject line for emails */}
        {activity.subject && (
          <p className="text-sm font-medium mt-2">
            Subject: {activity.subject}
          </p>
        )}

        {/* Content preview with expand */}
        {hasContent && (
          <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-2">
            <div
              className={`rounded-lg p-3 text-sm ${
                isReceived
                  ? "bg-blue-50 dark:bg-blue-950 border-l-4 border-blue-500"
                  : "bg-muted"
              }`}
            >
              {/* Preview (always shown) */}
              <p className={`whitespace-pre-wrap ${!isOpen && "line-clamp-2"}`}>
                {isOpen
                  ? activity.content_preview
                  : (activity.content_preview?.slice(0, 100) ?? "") +
                    ((activity.content_preview?.length ?? 0) > 100 ? "..." : "")}
              </p>

              {/* Actions */}
              <div className="flex items-center gap-2 mt-2">
                {(activity.content_preview?.length ?? 0) > 100 && (
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-7 text-xs">
                      {isOpen ? (
                        <>
                          <ChevronUp className="h-3 w-3 mr-1" />
                          Show less
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3 w-3 mr-1" />
                          Show more
                        </>
                      )}
                    </Button>
                  </CollapsibleTrigger>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="h-3 w-3 mr-1" />
                  ) : (
                    <Copy className="h-3 w-3 mr-1" />
                  )}
                  Copy
                </Button>
              </div>
            </div>
          </Collapsible>
        )}
      </div>
    </div>
  );
}

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  const { data: lead, isLoading: leadLoading, error: leadError, refetch: refetchLead } = useLead(params.id);
  const { data: activitiesData, isLoading: activitiesLoading } = useLeadActivities(params.id);

  if (leadLoading) {
    return <DetailPageSkeleton />;
  }

  if (leadError) {
    return (
      <div className="space-y-6">
        <Link href="/dashboard/leads">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Leads
          </Button>
        </Link>
        <ErrorState error={leadError} onRetry={refetchLead} />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="space-y-6">
        <Link href="/dashboard/leads">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Leads
          </Button>
        </Link>
        <EmptyState title="Lead not found" description="This lead may have been deleted" />
      </div>
    );
  }

  const tierColor = lead.als_tier ? getTierColor(lead.als_tier) : "bg-gray-500";
  const activities = activitiesData || [];

  // Build ALS components from lead data
  const alsComponents = {
    data_quality: lead.als_data_quality ?? 0,
    authority: lead.als_authority ?? 0,
    company_fit: lead.als_company_fit ?? 0,
    timing: lead.als_timing ?? 0,
    risk: lead.als_risk ?? 0,
  };

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
              {lead.first_name} {lead.last_name}
            </h1>
            {lead.als_score !== null && (
              <Badge className={tierColor}>
                ALS: {lead.als_score}
              </Badge>
            )}
            <Badge variant="secondary" className="capitalize">
              {lead.status.replace("_", " ")}
            </Badge>
          </div>
          <p className="text-lg text-muted-foreground">
            {lead.title && `${lead.title} at `}{lead.company || "Unknown Company"}
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
            {lead.linkedin_url && (
              <div className="flex items-center gap-3">
                <Linkedin className="h-4 w-4 text-muted-foreground" />
                <a
                  href={lead.linkedin_url}
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
            {lead.company && (
              <div className="flex items-center gap-3">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{lead.company}</span>
              </div>
            )}
            {lead.domain && (
              <div className="flex items-center gap-3">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <a
                  href={`https://${lead.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm hover:underline"
                >
                  {lead.domain}
                </a>
              </div>
            )}
            {lead.organization_country && (
              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">{lead.organization_country}</span>
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 pt-2 border-t">
              {lead.organization_industry && (
                <div>
                  <p className="text-xs text-muted-foreground">Industry</p>
                  <p className="text-sm font-medium">{lead.organization_industry}</p>
                </div>
              )}
              {lead.organization_employee_count && (
                <div>
                  <p className="text-xs text-muted-foreground">Size</p>
                  <p className="text-sm font-medium">{lead.organization_employee_count} employees</p>
                </div>
              )}
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
              href={`/dashboard/campaigns/${lead.campaign_id}`}
              className="text-sm font-medium hover:underline"
            >
              View Campaign
            </Link>
            <div className="grid grid-cols-2 gap-2 pt-2 border-t">
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <Badge variant="secondary" className="capitalize">
                  {lead.status.replace("_", " ")}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Created</p>
                <p className="text-sm font-medium">
                  {new Date(lead.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ALS Score Breakdown */}
      {lead.als_score !== null && (
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
                {lead.als_score}
              </div>
              <div>
                {lead.als_tier && (
                  <Badge className={`${tierColor} capitalize text-base px-3 py-1`}>
                    {lead.als_tier} Lead
                  </Badge>
                )}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-5">
              {Object.entries(alsComponents).map(([key, value]) => (
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
      )}

      {/* Activity Timeline with Content Visibility */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Timeline</CardTitle>
          <CardDescription>
            Recent interactions with this lead - click to expand message content
          </CardDescription>
        </CardHeader>
        <CardContent>
          {activitiesLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-4 animate-pulse">
                  <div className="h-3 w-3 rounded-full bg-muted" />
                  <div className="flex-1">
                    <div className="h-4 w-32 bg-muted rounded mb-2" />
                    <div className="h-3 w-24 bg-muted rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : activities.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="No activity yet"
              description="Outreach activity will appear here once the campaign starts"
              className="py-8"
            />
          ) : (
            <div className="space-y-0">
              {activities.map((activity, index) => (
                <ActivityTimelineItem
                  key={activity.id}
                  activity={activity}
                  isLast={index === activities.length - 1}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
