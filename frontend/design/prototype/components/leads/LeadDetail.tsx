"use client";

import {
  ArrowLeft,
  Mail,
  Phone,
  Linkedin,
  Building2,
  Globe,
  MapPin,
  Target,
} from "lucide-react";
import { DashboardShell } from "../layout";
import { ALSTierBadge, type ALSTier } from "./ALSTierBadge";
import { ALSScorecard, type ALSBreakdown } from "./ALSScorecard";
import { LeadTimeline, type ActivityItem } from "./LeadTimeline";
import { LeadEnrichment, type Signal } from "./LeadEnrichment";
import { LeadQuickActions } from "./LeadQuickActions";
import { LeadStatusProgress, type LeadStatus } from "./LeadStatusProgress";

/**
 * Demo lead data
 */
const demoLead = {
  id: "1",
  firstName: "Sarah",
  lastName: "Chen",
  email: "sarah@techcorp.io",
  phone: "+1 555-123-4567",
  linkedinUrl: "https://linkedin.com/in/sarahchen",
  title: "VP of Engineering",
  company: "TechCorp",
  industry: "Technology",
  size: "150 employees",
  location: "Sydney, Australia",
  website: "https://techcorp.io",
  tier: "hot" as ALSTier,
  status: "in_sequence" as LeadStatus,
  score: 87,
  breakdown: {
    dataQuality: 18,
    authority: 22,
    companyFit: 25,
    timing: 10,
    risk: 12,
  } as ALSBreakdown,
  signals: [
    { type: "hiring" as const, label: "Hiring", detail: "5 open roles" },
    { type: "funding" as const, label: "Funding", detail: "Series B - Q4 2025" },
  ] as Signal[],
  icebreaker:
    "Noticed your recent product launch announcement on LinkedIn. Scaling engineering teams during growth phase is challenging - we've helped 20+ companies like yours streamline their tech stack.",
  campaignName: "Tech Decision Makers",
  campaignId: "camp-1",
};

/**
 * Demo activity data
 */
const demoActivities: ActivityItem[] = [
  {
    id: "act-1",
    channel: "email",
    action: "Email sent",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    subject: "Quick question about scaling your engineering team",
    contentPreview: "Hi Sarah, I noticed TechCorp just raised Series B...",
    content: `Hi Sarah,

I noticed TechCorp just raised Series B and you're scaling your engineering team rapidly. Congrats on the growth!

At Agency OS, we've helped 20+ companies in similar growth phases streamline their outbound - freeing up time for their teams to focus on what matters.

Would you be open to a quick 15-min call this week to see if we might be a fit?

Best,
John`,
    sequenceStep: 1,
  },
  {
    id: "act-2",
    channel: "email",
    action: "Reply received",
    timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    intent: "positive",
    isReply: true,
    content: `Hi John,

Yes, we'd definitely be interested in learning more about your solution. We're drowning in outreach tasks right now and could use some help.

How does Thursday at 2pm AEST work for you?

Sarah`,
  },
  {
    id: "act-3",
    channel: "email",
    action: "Meeting booked",
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    subject: "Discovery Call",
    meetingTime: "Tomorrow 2:00 PM AEST",
  },
  {
    id: "act-4",
    channel: "linkedin",
    action: "LinkedIn connection sent",
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    contentPreview: "Hi Sarah, I came across your profile and was impressed by...",
  },
  {
    id: "act-5",
    channel: "linkedin",
    action: "LinkedIn connection accepted",
    timestamp: new Date(Date.now() - 2.5 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

/**
 * LeadDetail props
 */
export interface LeadDetailProps {
  /** Lead ID (for real implementation) */
  leadId?: string;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for navigation */
  onNavigate?: (path: string) => void;
  /** Handler for campaign click */
  onCampaignClick?: (campaignId: string) => void;
}

/**
 * Info card component
 */
function InfoCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      <div className="px-4 py-3 border-b border-[#E2E8F0]">
        <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">
          {title}
        </h3>
      </div>
      <div className="p-4 space-y-3">{children}</div>
    </div>
  );
}

/**
 * Info row component
 */
function InfoRow({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  href?: string;
}) {
  const content = (
    <div className="flex items-center gap-3">
      <div className="p-1.5 bg-[#F1F5F9] rounded-md">
        <Icon className="h-4 w-4 text-[#64748B]" />
      </div>
      <div>
        <p className="text-xs text-[#94A3B8]">{label}</p>
        <p
          className={`text-sm ${
            href ? "text-[#3B82F6] hover:underline" : "text-[#1E293B]"
          }`}
        >
          {value}
        </p>
      </div>
    </div>
  );

  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {content}
      </a>
    );
  }

  return content;
}

/**
 * LeadDetail - Full lead detail page component
 *
 * Features:
 * - Back button
 * - Lead name, tier badge, status progress
 * - Quick action buttons
 * - 3-column info grid: Contact, Company, Campaign
 * - ALS Scorecard
 * - Activity Timeline
 * - Enrichment data (Hot leads)
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Content background: #F8FAFC
 * - Card background: #FFFFFF
 * - Card border: #E2E8F0
 *
 * Usage:
 * ```tsx
 * <LeadDetail
 *   leadId="1"
 *   onBack={() => router.push('/leads')}
 * />
 * ```
 */
export function LeadDetail({
  leadId,
  onBack,
  onNavigate,
  onCampaignClick,
}: LeadDetailProps) {
  return (
    <DashboardShell
      title="Lead Detail"
      activePath="/leads"
      onNavigate={onNavigate}
      userName="Acme Agency"
    >
      <div className="space-y-6">
        {/* Back Button */}
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-[#64748B] hover:text-[#1E293B] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Leads
        </button>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-[#1E293B]">
                {demoLead.firstName} {demoLead.lastName}
              </h1>
              <ALSTierBadge tier={demoLead.tier} size="lg" />
            </div>
            <p className="text-[#64748B]">
              {demoLead.title} at {demoLead.company}
            </p>
            <div className="mt-4">
              <LeadStatusProgress status={demoLead.status} />
            </div>
          </div>
          <LeadQuickActions
            onPause={() => console.log("Pause")}
            onArchive={() => console.log("Archive")}
            onPrioritize={() => console.log("Prioritize")}
            onRescore={() => console.log("Rescore")}
          />
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Contact Info */}
          <InfoCard title="Contact">
            <InfoRow
              icon={Mail}
              label="Email"
              value={demoLead.email}
              href={`mailto:${demoLead.email}`}
            />
            {demoLead.phone && (
              <InfoRow
                icon={Phone}
                label="Phone"
                value={demoLead.phone}
                href={`tel:${demoLead.phone}`}
              />
            )}
            {demoLead.linkedinUrl && (
              <InfoRow
                icon={Linkedin}
                label="LinkedIn"
                value="View Profile"
                href={demoLead.linkedinUrl}
              />
            )}
          </InfoCard>

          {/* Company Info */}
          <InfoCard title="Company">
            <InfoRow
              icon={Building2}
              label="Company"
              value={demoLead.company}
            />
            <InfoRow icon={Globe} label="Website" value={demoLead.website || ""} href={demoLead.website} />
            <InfoRow icon={MapPin} label="Location" value={demoLead.location} />
            <p className="text-xs text-[#94A3B8] ml-10">
              {demoLead.size} - {demoLead.industry}
            </p>
          </InfoCard>

          {/* Campaign Info */}
          <InfoCard title="Campaign">
            <div className="flex items-center gap-3">
              <div className="p-1.5 bg-[#F1F5F9] rounded-md">
                <Target className="h-4 w-4 text-[#64748B]" />
              </div>
              <div>
                <p className="text-xs text-[#94A3B8]">Active Campaign</p>
                <p className="text-sm text-[#1E293B]">{demoLead.campaignName}</p>
              </div>
            </div>
            <button
              onClick={() => onCampaignClick?.(demoLead.campaignId)}
              className="w-full mt-2 px-3 py-2 bg-[#F1F5F9] hover:bg-[#E2E8F0] text-sm text-[#64748B] rounded-lg transition-colors"
            >
              View Campaign
            </button>
          </InfoCard>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            {/* ALS Scorecard */}
            <ALSScorecard score={demoLead.score} breakdown={demoLead.breakdown} />

            {/* Enrichment (Hot leads only) */}
            {demoLead.tier === "hot" && (
              <LeadEnrichment
                company={demoLead.company}
                industry={demoLead.industry}
                size={demoLead.size}
                location={demoLead.location}
                website={demoLead.website}
                signals={demoLead.signals}
                icebreaker={demoLead.icebreaker}
              />
            )}
          </div>

          {/* Right Column */}
          <div>
            {/* Activity Timeline */}
            <LeadTimeline activities={demoActivities} />
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}

export default LeadDetail;
