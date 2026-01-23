"use client";

import { Building2, MapPin, Users, Quote, TrendingUp, Briefcase } from "lucide-react";

/**
 * Signal type
 */
export interface Signal {
  /** Signal type */
  type: "hiring" | "funding" | "growth" | "news";
  /** Signal label */
  label: string;
  /** Signal detail */
  detail?: string;
}

/**
 * LeadEnrichment props
 */
export interface LeadEnrichmentProps {
  /** Company name */
  company: string;
  /** Industry */
  industry?: string;
  /** Company size description */
  size?: string;
  /** Company location */
  location?: string;
  /** Company website */
  website?: string;
  /** Active signals */
  signals?: Signal[];
  /** Icebreaker hook (Hot leads only) */
  icebreaker?: string;
}

/**
 * Signal badge configuration
 */
const signalConfig: Record<
  string,
  { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }
> = {
  hiring: { bg: "bg-[#DBEAFE]", text: "text-[#1E40AF]", icon: Briefcase },
  funding: { bg: "bg-[#D1FAE5]", text: "text-[#065F46]", icon: TrendingUp },
  growth: { bg: "bg-[#FEF3C7]", text: "text-[#92400E]", icon: TrendingUp },
  news: { bg: "bg-[#EDE9FE]", text: "text-[#5B21B6]", icon: TrendingUp },
};

/**
 * LeadEnrichment - Enrichment data card component
 *
 * Features:
 * - Company information section
 * - Signals badges (Hiring, Funding, etc.)
 * - Icebreaker quote (Hot leads only)
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF (card-bg)
 * - Card border: #E2E8F0 (card-border)
 * - Text primary: #1E293B (text-primary)
 * - Text secondary: #64748B (text-secondary)
 *
 * Usage:
 * ```tsx
 * <LeadEnrichment
 *   company="TechCorp"
 *   industry="Technology"
 *   size="50-200 employees"
 *   location="Sydney, Australia"
 *   signals={[{ type: "hiring", label: "Hiring", detail: "5 open roles" }]}
 *   icebreaker="Noticed your recent product launch..."
 * />
 * ```
 */
export function LeadEnrichment({
  company,
  industry,
  size,
  location,
  website,
  signals = [],
  icebreaker,
}: LeadEnrichmentProps) {
  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Enrichment Data
        </h2>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Company Info */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#F1F5F9] rounded-lg">
              <Building2 className="h-5 w-5 text-[#64748B]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#1E293B]">{company}</p>
              {industry && (
                <p className="text-xs text-[#64748B]">{industry}</p>
              )}
            </div>
          </div>

          {size && (
            <div className="flex items-center gap-3">
              <div className="p-2 bg-[#F1F5F9] rounded-lg">
                <Users className="h-5 w-5 text-[#64748B]" />
              </div>
              <p className="text-sm text-[#64748B]">{size}</p>
            </div>
          )}

          {location && (
            <div className="flex items-center gap-3">
              <div className="p-2 bg-[#F1F5F9] rounded-lg">
                <MapPin className="h-5 w-5 text-[#64748B]" />
              </div>
              <p className="text-sm text-[#64748B]">{location}</p>
            </div>
          )}

          {website && (
            <div className="ml-12">
              <a
                href={website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[#3B82F6] hover:text-[#2563EB] hover:underline transition-colors"
              >
                {website.replace(/^https?:\/\//, "")}
              </a>
            </div>
          )}
        </div>

        {/* Signals */}
        {signals.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider mb-3">
              Signals
            </h3>
            <div className="flex flex-wrap gap-2">
              {signals.map((signal, index) => {
                const config = signalConfig[signal.type] || signalConfig.news;
                const Icon = config.icon;

                return (
                  <div
                    key={index}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${config.bg}`}
                  >
                    <Icon className={`h-3.5 w-3.5 ${config.text}`} />
                    <span className={`text-xs font-medium ${config.text}`}>
                      {signal.label}
                    </span>
                    {signal.detail && (
                      <span className={`text-xs ${config.text} opacity-75`}>
                        - {signal.detail}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Icebreaker */}
        {icebreaker && (
          <div>
            <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider mb-3">
              Icebreaker
            </h3>
            <div className="bg-[#FEF3C7] border border-[#FCD34D] rounded-lg p-4">
              <div className="flex gap-3">
                <Quote className="h-5 w-5 text-[#D97706] flex-shrink-0 mt-0.5" />
                <p className="text-sm text-[#92400E] italic">
                  &quot;{icebreaker}&quot;
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default LeadEnrichment;
