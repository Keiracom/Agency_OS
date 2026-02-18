// Shared types for Agency OS frontend
// Single source of truth for types used across multiple modules
// CEO Directive #027 — Design System Overhaul: Lucide icons only

export type ChannelType = 'email' | 'linkedin' | 'voice' | 'sms' | 'mail';

// Channel icon names (Lucide icon identifiers)
// Usage: import { Mail, Briefcase, Phone, MessageSquare, Send } from 'lucide-react'
export const channelIconName: Record<ChannelType, string> = {
  email: 'Mail',
  linkedin: 'Linkedin',
  voice: 'Phone',
  sms: 'MessageSquare',
  mail: 'Send',
};

// Legacy emoji mapping — DEPRECATED, use channelIconName instead
// Keeping for backward compatibility during migration
export const channelEmoji: Record<ChannelType, string> = {
  email: 'Mail',
  linkedin: 'Linkedin',
  voice: 'Phone',
  sms: 'MessageSquare',
  mail: 'Send',
};
