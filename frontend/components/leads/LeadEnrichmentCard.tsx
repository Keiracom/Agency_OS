"use client";

/**
 * LeadEnrichmentCard.tsx - Lead Enrichment Data Display
 * Phase I: Dashboard Redesign - Component #26
 *
 * Displays enrichment information for a lead:
 * - Company info (name, industry, size, location)
 * - Contact details (email, phone, LinkedIn)
 * - SDK enrichment signals (funding, hiring, etc.)
 * - Icebreaker hooks for Hot leads
 * - Enrichment confidence and timestamps
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Lead, SDKEnrichmentData } from "@/lib/api/types";
import { DeepResearchData } from "@/lib/api/leads";
import { cn } from "@/lib/utils";
import {
  Building2,
  Mail,
  Phone,
  Linkedin,
  Globe,
  Users,
  DollarSign,
  Calendar,
  TrendingUp,
  Briefcase,
  MapPin,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Clock,
} from "lucide-react";

// ============================================
// Types
// ============================================

interface LeadEnrichmentCardProps {
  lead: Lead;
  research?: DeepResearchData | null;
  showInternalDetails?: boolean; // Admin only - shows cost, confidence
  isLoading?: boolean;
  error?: Error | null;
  className?: string;
}

// ============================================
// Helper Functions
// ============================================

/**
 * Format employee count to readable string
 */
function formatEmployeeCount(count: number | null | undefined): string {
  if (!count) return "Unknown";
  if (count < 10) return "1-10";
  if (count < 50) return "10-50";
  if (count < 200) return "50-200";
  if (count < 500) return "200-500";
  if (count < 1000) return "500-1K";
  if (count < 5000) return "1K-5K";
  return "5K+";
}

/**
 * Format date to relative time
 */
function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return "Unknown";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

/**
 * Get signal badge variant
 */
function getSignalVariant(signal: string): "default" | "secondary" | "outline" {
  const lowerSignal = signal.toLowerCase();
  if (lowerSignal.includes("funding") || lowerSignal.includes("hiring")) {
    return "default";
  }
  if (lowerSignal.includes("tech") || lowerSignal.includes("match")) {
    return "secondary";
  }
  return "outline";
}

// ============================================
// Loading Skeleton
// ============================================

function EnrichmentCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Company Section */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <div className="grid grid-cols-2 gap-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
        {/* Contact Section */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-16" />
          <div className="grid grid-cols-2 gap-2">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-4 w-28" />
          </div>
        </div>
        {/* Signals */}
        <div className="flex gap-1">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================
// Error State
// ============================================

function EnrichmentCardError({ error }: { error: Error }) {
  return (
    <Card className="border-destructive/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertCircle className="h-4 w-4 text-destructive" />
          Enrichment Error
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          {error.message || "Failed to load enrichment data"}
        </p>
      </CardContent>
    </Card>
  );
}

// ============================================
// Empty State
// ============================================

function EnrichmentCardEmpty() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Building2 className="h-4 w-4" />
          Enrichment Data
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          No enrichment data available for this lead yet.
        </p>
      </CardContent>
    </Card>
  );
}

// ============================================
// Main Component
// ============================================

export function LeadEnrichmentCard({
  lead,
  research,
  showInternalDetails = false,
  isLoading = false,
  error = null,
  className,
}: LeadEnrichmentCardProps) {
  // Loading state
  if (isLoading) {
    return <EnrichmentCardSkeleton />;
  }

  // Error state
  if (error) {
    return <EnrichmentCardError error={error} />;
  }

  const enrichment: SDKEnrichmentData = lead.sdk_enrichment || {};
  const signals = lead.sdk_signals || [];
  const hasEnrichmentData =
    lead.company ||
    lead.organization_industry ||
    lead.organization_employee_count ||
    lead.email ||
    lead.phone ||
    lead.linkedin_url ||
    Object.keys(enrichment).length > 0;

  // Empty state - no data to show
  if (!hasEnrichmentData) {
    return <EnrichmentCardEmpty />;
  }

  const isHotLead = lead.als_tier === "hot" || (lead.als_score && lead.als_score >= 85);
  const hasSDKEnrichment = lead.sdk_enriched_at !== null;

  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Enrichment Data
          </span>
          {hasSDKEnrichment && (
            <Badge variant="secondary" className="text-xs">
              <Sparkles className="h-3 w-3 mr-1" />
              SDK Enhanced
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Company Information */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
            <Building2 className="h-3 w-3" />
            Company
          </h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {lead.company && (
              <div className="flex items-center gap-2">
                <Building2 className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <span className="truncate">{lead.company}</span>
              </div>
            )}
            {lead.organization_industry && (
              <div className="flex items-center gap-2">
                <Briefcase className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <span className="truncate">{lead.organization_industry}</span>
              </div>
            )}
            {(lead.organization_employee_count || enrichment.company_size) && (
              <div className="flex items-center gap-2">
                <Users className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <span>
                  {enrichment.company_size || formatEmployeeCount(lead.organization_employee_count)}
                </span>
              </div>
            )}
            {lead.organization_country && (
              <div className="flex items-center gap-2">
                <MapPin className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <span>{lead.organization_country}</span>
              </div>
            )}
            {enrichment.company_website && (
              <div className="flex items-center gap-2">
                <Globe className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <a
                  href={enrichment.company_website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline truncate"
                >
                  Website
                </a>
              </div>
            )}
            {enrichment.company_revenue && (
              <div className="flex items-center gap-2">
                <DollarSign className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <span>{enrichment.company_revenue}</span>
              </div>
            )}
          </div>
        </div>

        {/* Contact Information */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
            <Mail className="h-3 w-3" />
            Contact
          </h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {lead.email && (
              <div className="flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <a
                  href={`mailto:${lead.email}`}
                  className="text-primary hover:underline truncate"
                >
                  {lead.email}
                </a>
              </div>
            )}
            {lead.phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <a
                  href={`tel:${lead.phone}`}
                  className="text-primary hover:underline"
                >
                  {lead.phone}
                </a>
              </div>
            )}
            {lead.linkedin_url && (
              <div className="flex items-center gap-2">
                <Linkedin className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                <a
                  href={lead.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  LinkedIn Profile
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Signals */}
        {signals.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              Signals
            </h4>
            <div className="flex flex-wrap gap-1">
              {signals.map((signal, idx) => (
                <Badge
                  key={idx}
                  variant={getSignalVariant(signal)}
                  className="text-xs"
                >
                  {signal}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Funding Signal */}
        {enrichment.recent_funding && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <DollarSign className="h-3 w-3" />
              Recent Funding
            </h4>
            <div className="text-sm bg-muted/50 rounded-md p-2">
              {enrichment.recent_funding.round && (
                <span className="font-medium">{enrichment.recent_funding.round}</span>
              )}
              {enrichment.recent_funding.amount && (
                <span> - {enrichment.recent_funding.amount}</span>
              )}
              {enrichment.recent_funding.date && (
                <span className="text-muted-foreground">
                  {" "}({formatRelativeTime(enrichment.recent_funding.date)})
                </span>
              )}
            </div>
          </div>
        )}

        {/* Hiring Signals */}
        {enrichment.hiring_signals && enrichment.hiring_signals.open_roles && enrichment.hiring_signals.open_roles > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <Users className="h-3 w-3" />
              Hiring Activity
            </h4>
            <div className="text-sm">
              <Badge variant="secondary">
                {enrichment.hiring_signals.open_roles} open roles
              </Badge>
            </div>
          </div>
        )}

        {/* Icebreaker (Hot leads with research) */}
        {isHotLead && research?.icebreaker_hook && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              Icebreaker
            </h4>
            <div className="text-sm bg-primary/5 border border-primary/20 rounded-md p-3 italic">
              "{research.icebreaker_hook}"
            </div>
          </div>
        )}

        {/* Alternative: SDK enrichment icebreakers */}
        {!research?.icebreaker_hook && enrichment.icebreaker_hooks && enrichment.icebreaker_hooks.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              Icebreakers
            </h4>
            <ul className="text-sm space-y-1">
              {enrichment.icebreaker_hooks.slice(0, 3).map((hook, idx) => (
                <li key={idx} className="bg-primary/5 border border-primary/20 rounded-md p-2 italic text-sm">
                  "{hook}"
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Research Summary (Hot leads) */}
        {research?.profile_summary && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Research Summary
            </h4>
            <p className="text-sm text-muted-foreground">
              {research.profile_summary}
            </p>
          </div>
        )}

        {/* Internal Details (Admin only) */}
        {showInternalDetails && (
          <div className="pt-2 border-t border-border space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">
              Internal Details
            </h4>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
              {lead.sdk_cost_aud !== null && lead.sdk_cost_aud !== undefined && (
                <div className="flex items-center gap-1">
                  <DollarSign className="h-3 w-3" />
                  <span>SDK Cost: ${lead.sdk_cost_aud.toFixed(2)}</span>
                </div>
              )}
              {enrichment.confidence_score !== null && enrichment.confidence_score !== undefined && (
                <div className="flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>Confidence: {Math.round(enrichment.confidence_score * 100)}%</span>
                </div>
              )}
              {research?.confidence !== null && research?.confidence !== undefined && (
                <div className="flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>Research Confidence: {Math.round(research.confidence * 100)}%</span>
                </div>
              )}
              {lead.sdk_enriched_at && (
                <div className="flex items-center gap-1 col-span-2">
                  <Clock className="h-3 w-3" />
                  <span>Enriched: {formatRelativeTime(lead.sdk_enriched_at)}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Enrichment Timestamp (Non-admin) */}
        {!showInternalDetails && lead.sdk_enriched_at && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2">
            <Calendar className="h-3 w-3" />
            <span>Enriched {formatRelativeTime(lead.sdk_enriched_at)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default LeadEnrichmentCard;
