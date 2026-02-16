"use client";

/**
 * CoPilotView.tsx - The Glass Box Co-Pilot Interface
 * Phase 20: UI Wiring
 * TASK: WIRE-003
 *
 * Split-screen layout:
 * - Left: Draft Email composer
 * - Right: Context Cards (LinkedIn posts, website value prop, ALS breakdown)
 *
 * Now wired to real deep research API data.
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Send,
  RefreshCw,
  Linkedin,
  Globe,
  BarChart3,
  Sparkles,
  Copy,
  Check,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useDeepResearch, useTriggerDeepResearch } from "@/hooks/use-deep-research";
import type { DeepResearchData } from "@/lib/api/leads";

interface LeadData {
  id: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  title?: string;
  email?: string;
  linkedin_url?: string;
  als_score?: number;
  als_tier?: string;
  als_data_quality?: number;
  als_authority?: number;
  als_company_fit?: number;
  als_timing?: number;
  als_risk?: number;
  deep_research_run_at?: string;
}

interface CoPilotViewProps {
  lead: LeadData;
  onSendEmail?: (content: string) => void;
  onRegenerateEmail?: () => void;
}

export function CoPilotView({
  lead,
  onSendEmail,
  onRegenerateEmail,
}: CoPilotViewProps) {
  const {
    data: research,
    isLoading: isLoadingResearch,
    isResearching,
    isComplete,
    hasFailed,
    notStarted,
  } = useDeepResearch(lead.id);

  const triggerResearch = useTriggerDeepResearch();

  const [emailContent, setEmailContent] = useState("");
  const [copied, setCopied] = useState(false);

  // Update email content when research data is available
  useEffect(() => {
    const firstName = lead.first_name || "there";
    const icebreaker = research?.icebreaker_hook ||
      `I noticed ${lead.company || "your company"} and thought we might be a good fit.`;

    setEmailContent(
`Hi ${firstName},

${icebreaker}

We've helped similar agencies book 40+ qualified meetings per month using our multi-channel approach. Given your focus on ${lead.company ? `${lead.company}'s growth` : "agency growth"}, I think our compliance-first platform could be a great fit.

Would you be open to a quick 15-min call next week to explore?

Best,
[Your name]`
    );
  }, [lead, research?.icebreaker_hook]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(emailContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTriggerResearch = () => {
    triggerResearch.mutate({ leadId: lead.id, force: hasFailed });
  };

  const getTierColor = (tier: string | undefined) => {
    switch (tier?.toLowerCase()) {
      case "hot":
        return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "warm":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
      case "cool":
        return "bg-bg-elevated/20 text-text-secondary border-default/30";
      case "cold":
        return "bg-bg-surface0/20 text-text-muted border-gray-500/30";
      default:
        return "bg-bg-surface0/20 text-text-muted border-gray-500/30";
    }
  };

  const fullName = [lead.first_name, lead.last_name].filter(Boolean).join(" ") || "Lead";
  const emailDomain = lead.email?.split("@")[1] || (lead.company?.toLowerCase().replace(/\s+/g, "") + ".com");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 bg-[#0f0f13] min-h-screen">
      {/* Left Panel: Email Composer */}
      <div className="space-y-4">
        <Card className="bg-[#1a1a1f] border-white/10">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-text-primary flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-amber" />
                Draft Email
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge className={getTierColor(lead.als_tier)}>
                  {lead.als_tier || "Unscored"} ({lead.als_score || 0})
                </Badge>
              </div>
            </div>
            <p className="text-sm text-text-muted">
              To: {fullName} &lt;{lead.email || `${fullName.toLowerCase().replace(" ", ".")}@${emailDomain}`}&gt;
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs text-text-primary0 uppercase tracking-wider">
                Subject
              </label>
              <input
                type="text"
                className="w-full bg-[#0f0f13] border border-white/10 rounded-md px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-amber/50"
                defaultValue={`Quick question about ${lead.company || "your"}'s marketing tech stack`}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-text-primary0 uppercase tracking-wider">
                Body
              </label>
              <Textarea
                value={emailContent}
                onChange={(e) => setEmailContent(e.target.value)}
                className="min-h-[300px] bg-[#0f0f13] border-white/10 text-text-primary resize-none focus:ring-2 focus:ring-amber/50"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => onSendEmail?.(emailContent)}
                className="flex-1 bg-gradient-to-r from-amber to-amber hover:from-amber hover:to-amber"
              >
                <Send className="h-4 w-4 mr-2" />
                Send Email
              </Button>
              <Button
                variant="outline"
                onClick={onRegenerateEmail}
                className="border-white/10 text-text-secondary hover:bg-bg-surface/5"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Regenerate
              </Button>
              <Button
                variant="outline"
                onClick={handleCopy}
                className="border-white/10 text-text-secondary hover:bg-bg-surface/5"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-amber" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Panel: Context Cards */}
      <div className="space-y-4">
        {/* Research Status Banner */}
        {isLoadingResearch ? (
          <Card className="bg-[#1a1a1f] border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Skeleton className="h-5 w-5 rounded-full" />
                <Skeleton className="h-4 w-48" />
              </div>
            </CardContent>
          </Card>
        ) : isResearching ? (
          <Card className="bg-bg-void/20 border-default/30">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 text-text-secondary">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Deep research in progress...</span>
              </div>
            </CardContent>
          </Card>
        ) : hasFailed ? (
          <Card className="bg-red-900/20 border-amber/30">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-amber">
                  <AlertCircle className="h-5 w-5" />
                  <span>Research failed: {research?.error}</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleTriggerResearch}
                  disabled={triggerResearch.isPending}
                  className="border-amber/30 text-amber hover:bg-amber-glow"
                >
                  {triggerResearch.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Retry"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : notStarted && lead.linkedin_url ? (
          <Card className="bg-yellow-900/20 border-yellow-500/30">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-yellow-400">
                  <Sparkles className="h-5 w-5" />
                  <span>Deep research available</span>
                </div>
                <Button
                  size="sm"
                  onClick={handleTriggerResearch}
                  disabled={triggerResearch.isPending}
                  className="bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-500 hover:to-amber-light"
                >
                  {triggerResearch.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-2" />
                  )}
                  Run Research
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* LinkedIn Post Card */}
        {isComplete && research?.social_posts && research.social_posts.length > 0 && (
          <Card className="bg-[#1a1a1f] border-white/10">
            <CardHeader className="pb-2">
              <CardTitle className="text-text-primary text-sm flex items-center gap-2">
                <Linkedin className="h-4 w-4 text-text-secondary" />
                Recent LinkedIn Posts
                <span className="text-text-primary0 font-normal">
                  ({research.posts_found} found)
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {research.social_posts.slice(0, 3).map((post, index) => (
                <div key={post.id || index} className="p-3 bg-[#0f0f13] rounded-lg">
                  <p className="text-text-secondary text-sm leading-relaxed line-clamp-3">
                    "{post.content}"
                  </p>
                  {post.date && (
                    <p className="text-text-primary0 text-xs mt-2">
                      {new Date(post.date).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Profile Summary Card */}
        {isComplete && research?.profile_summary && (
          <Card className="bg-[#1a1a1f] border-white/10">
            <CardHeader className="pb-2">
              <CardTitle className="text-text-primary text-sm flex items-center gap-2">
                <Globe className="h-4 w-4 text-amber" />
                Profile Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-text-secondary text-sm leading-relaxed">
                {research.profile_summary}
              </p>
            </CardContent>
          </Card>
        )}

        {/* ALS Score Breakdown Card */}
        {(lead.als_data_quality !== undefined || lead.als_score !== undefined) && (
          <Card className="bg-[#1a1a1f] border-white/10">
            <CardHeader className="pb-2">
              <CardTitle className="text-text-primary text-sm flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-amber" />
                ALS Score Breakdown
                <Badge className={getTierColor(lead.als_tier)}>
                  {lead.als_score || 0}/100
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "Data Quality", value: lead.als_data_quality || 0, max: 20 },
                { label: "Authority", value: lead.als_authority || 0, max: 25 },
                { label: "Company Fit", value: lead.als_company_fit || 0, max: 25 },
                { label: "Timing", value: lead.als_timing || 0, max: 15 },
                { label: "Risk", value: lead.als_risk || 0, max: 15 },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">{item.label}</span>
                    <span className="text-text-primary">
                      {item.value}/{item.max}
                    </span>
                  </div>
                  <div className="h-2 bg-bg-base rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber to-amber rounded-full transition-all"
                      style={{ width: `${(item.value / item.max) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* AI Icebreaker Suggestion */}
        {isComplete && research?.icebreaker_hook && (
          <Card className="bg-gradient-to-br from-purple-900/20 to-bg-void/20 border-amber/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-text-primary text-sm flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber" />
                AI Icebreaker Suggestion
                {research.confidence && (
                  <Badge variant="outline" className="ml-2 text-xs border-amber/30 text-amber">
                    {Math.round(research.confidence * 100)}% confidence
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-amber-light text-sm italic">
                "{research.icebreaker_hook}"
              </p>
            </CardContent>
          </Card>
        )}

        {/* No LinkedIn URL Warning */}
        {!lead.linkedin_url && (
          <Card className="bg-bg-void/20 border-gray-500/30">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 text-text-muted">
                <Linkedin className="h-5 w-5" />
                <span>No LinkedIn URL available. Add LinkedIn to enable deep research.</span>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default CoPilotView;
