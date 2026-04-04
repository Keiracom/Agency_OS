/**
 * FILE: lib/types/prospect-card.ts
 * PURPOSE: ProspectCard TypeScript types matching pipeline_orchestrator.py ProspectCard dataclass
 * SOURCE: src/pipeline/pipeline_orchestrator.py — ProspectCard @dataclass
 */

export type VulnGrade = "A" | "B" | "C" | "D" | "F";

export interface VulnSection {
  grade: VulnGrade;
  findings: string;
  priority_action: string;
}

export interface VulnerabilityReport {
  overall_grade: VulnGrade;
  three_month_roadmap: string[];
  search_visibility: VulnSection;
  technical_seo: VulnSection;
  backlinks: VulnSection;
  paid_ads: VulnSection;
  reputation: VulnSection;
  competitive_position: VulnSection;
}

/** Intent bands from the pipeline scoring engine */
export type IntentBand =
  | "STRUGGLING"
  | "TRYING"
  | "DABBLING"
  | "NOT_TRYING"
  | "UNKNOWN";

/** Affordability bands from the pipeline scoring engine */
export type AffordabilityBand = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

/** DM contact confidence level */
export type DMConfidence = "HIGH" | "MEDIUM" | "LOW";

/**
 * ProspectCard — mirrors Python ProspectCard dataclass plus extended
 * intelligence/outreach fields written by the pipeline stages.
 */
export interface ProspectCard {
  // Core identity
  domain: string;
  company_name: string;
  location: string;
  location_suburb: string;
  location_state: string;
  location_display: string;

  // Scoring
  affordability_band: AffordabilityBand;
  affordability_score: number;
  intent_band: IntentBand;
  intent_score: number;

  // Services & evidence
  services: string[];
  evidence: string[];

  // Intelligence signals (from stage 7 Haiku / stage 7b intelligence)
  headline_signal: string | null;
  recommended_service: string | null;
  outreach_angle: string | null;

  // DM contact
  dm_name: string | null;
  dm_title: string | null;
  dm_email: string | null;
  dm_email_verified: boolean;
  dm_email_source: string | null;
  dm_email_confidence: string | null;
  dm_mobile: string | null;
  dm_linkedin_url: string | null;
  dm_confidence: DMConfidence | null;

  // Draft outreach (from outreach_messages JSONB)
  draft_email_subject: string | null;
  draft_email_body: string | null;

  // GMB
  gmb_rating: number | null;
  gmb_review_count: number;

  // Paid ads
  is_running_ads: boolean;

  // Competitive intelligence
  competitors_top3: string[];
  competitor_count: number;

  // Backlinks / SEO
  referring_domains: number;
  domain_rank: number;
  backlink_trend: string;

  // Brand SERP
  brand_position: number | null;
  brand_gmb_showing: boolean;
  brand_competitors_bidding: boolean;

  // Technical
  indexed_pages: number;
  email_cost_usd: number;

  // Vulnerability report
  vulnerability_report: VulnerabilityReport | null;

  // Pipeline metadata
  pipeline_stage?: number;
  pipeline_updated_at?: string;
}
