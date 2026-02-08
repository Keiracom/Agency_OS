/**
 * lead.ts - Lead TypeScript Interfaces
 * Phase: Operation Modular Cockpit
 * 
 * Matches future `leads` table with JSONB transcript fields
 * Ready for Supabase integration
 */

// ============================================
// Core Types
// ============================================

export type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";

export type ChannelType = "email" | "linkedin" | "voice" | "sms" | "mail";

export type WhyHotCategory = 
  | "executive" 
  | "active" 
  | "buyer" 
  | "linkedin" 
  | "timing";

// ============================================
// Transcript Types (JSONB fields)
// ============================================

export interface TranscriptLine {
  speaker: "ai" | "lead";
  speakerName: string;
  timestamp: string; // "0:00" format
  text: string;
  highlight?: {
    type: "pain_point" | "meeting_intent" | "meeting_booked" | "objection";
    label: string;
  };
}

export interface CallLog {
  id: string;
  type: "voice" | "email" | "linkedin" | "sms";
  direction: "outbound" | "inbound";
  timestamp: string; // ISO datetime
  duration?: number; // seconds for voice calls
  subject?: string; // for emails
  summary: string;
  outcome?: "booked" | "replied" | "opened" | "connected" | "no_answer" | "voicemail";
  transcript?: TranscriptLine[]; // for voice calls
}

export interface EmailMessage {
  id: string;
  sender: string;
  timestamp: string;
  subject: string;
  body: string;
  direction: "sent" | "received";
}

export interface LinkedInMessage {
  id: string;
  sender: string;
  timestamp: string;
  text: string;
  direction: "sent" | "received";
  isConnectionAccepted?: boolean;
}

// ============================================
// Engagement Profile (Radar Chart Data)
// ============================================

export interface EngagementScore {
  label: string;
  value: number;
  maxValue: number;
  level: "high" | "medium" | "low";
}

export interface EngagementProfile {
  dataQuality: EngagementScore;
  authority: EngagementScore;
  companyFit: EngagementScore;
  timing: EngagementScore;
  engagement: EngagementScore;
}

// ============================================
// Why Hot Badge
// ============================================

export interface WhyHotBadge {
  id: string;
  category: WhyHotCategory;
  label: string;
  icon?: string;
}

// ============================================
// Company Intel
// ============================================

export interface CompanyIntel {
  id: string;
  name: string;
  domain: string;
  logoEmoji?: string;
  employees: string;
  industry: string;
  estimatedRevenue: string;
  location: string;
  recentIntelligence: {
    icon: string;
    text: string;
  }[];
}

// ============================================
// Activity Timeline Event
// ============================================

export interface TimelineEvent {
  id: string;
  type: ChannelType | "reply";
  title: string;
  detail?: string;
  timestamp: string; // ISO datetime
  displayTime: string; // "10:42 AM"
  badge?: {
    type: "booked" | "replied" | "positive";
    label: string;
  };
  hasTranscript?: boolean;
  hasThread?: boolean;
}

export interface TimelineDay {
  date: string; // "Today", "Yesterday", "Jan 29, 2026"
  isToday?: boolean;
  events: TimelineEvent[];
}

// ============================================
// Note
// ============================================

export interface LeadNote {
  id: string;
  author: string;
  timestamp: string;
  text: string;
}

// ============================================
// Full Lead Type
// ============================================

export interface Lead {
  id: string;
  
  // Basic Info
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  linkedinUrl?: string;
  title: string;
  
  // Company
  company: CompanyIntel;
  
  // Scoring
  score: number;
  tier: ALSTier;
  whyHot: WhyHotBadge[];
  engagementProfile: EngagementProfile;
  
  // Activity (JSONB in DB)
  timeline: TimelineDay[];
  callLogs: CallLog[];
  emailThread: EmailMessage[];
  linkedinThread: LinkedInMessage[];
  
  // Notes
  notes: LeadNote[];
  
  // Metadata
  createdAt: string;
  updatedAt: string;
}

// ============================================
// Modal Props
// ============================================

export interface LeadDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  lead: Lead | null;
}
