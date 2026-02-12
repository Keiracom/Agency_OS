/**
 * FILE: frontend/components/inbox/ChannelBadge.tsx
 * PURPOSE: Channel indicator badge component
 */
import { ChannelType, channelLabels } from '@/lib/mock/inbox-data';
import { Mail, Linkedin, MessageSquare, Phone } from 'lucide-react';
import { cn } from '@/lib/utils';

const channelIcons: Record<ChannelType, typeof Mail> = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  voice: Phone,
};

const channelStyles: Record<ChannelType, string> = {
  email: 'text-accent-primary',
  linkedin: 'text-[#0A66C2]',
  sms: 'text-teal-400',
  voice: 'text-status-warning',
};

export function ChannelBadge({ channel }: { channel: ChannelType }) {
  const Icon = channelIcons[channel];
  return (
    <span className={cn(
      'flex items-center gap-1 px-2 py-0.5 bg-white/5 rounded text-[11px]',
      channelStyles[channel]
    )}>
      <Icon className="w-3.5 h-3.5" />
      {channelLabels[channel]}
    </span>
  );
}
