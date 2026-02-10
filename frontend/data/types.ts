// Shared types for Agency OS frontend
// Single source of truth for types used across multiple modules

export type ChannelType = 'email' | 'linkedin' | 'voice' | 'sms' | 'mail';

// Channel emoji mapping
export const channelEmoji: Record<ChannelType, string> = {
  email: '📧',
  linkedin: '💼',
  voice: '📞',
  sms: '💬',
  mail: '📬',
};
