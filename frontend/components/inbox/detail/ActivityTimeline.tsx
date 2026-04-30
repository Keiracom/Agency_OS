/**
 * FILE: frontend/components/inbox/detail/ActivityTimeline.tsx
 * PURPOSE: Activity timeline in sidebar
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { ActivityItem, ChannelType } from '@/lib/mock/inbox-data';
import { Clock, Mail, MessageCircle, Linkedin, Phone } from 'lucide-react';
import { cn } from '@/lib/utils';

const channelIcons: Record<ChannelType, typeof Mail> = {
  email: Mail,
  sms: MessageCircle,
  linkedin: Linkedin,
  voice: Phone,
};

const channelColors: Record<ChannelType, string> = {
  email: 'bg-amber/15 text-amber',
  sms: 'bg-amber-glow text-amber',
  linkedin: 'bg-bg-elevated/15 text-ink-2',
  voice: 'bg-amber-500/15 text-amber-400',
};

interface ActivityTimelineProps {
  activities: ActivityItem[];
}

export function ActivityTimeline({ activities }: ActivityTimelineProps) {
  return (
    <div className="bg-bg-surface rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-ink-3">
        <Clock className="w-3.5 h-3.5" />
        Related Activity
      </div>
      <div className="space-y-3">
        {activities.map((activity) => {
          const IconComponent = channelIcons[activity.channel];
          
          return (
            <div key={activity.id} className="flex items-start gap-2.5">
              <div className={cn('w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0', channelColors[activity.channel])}>
                <IconComponent className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-ink-2 leading-snug">{activity.text}</p>
                <p className="text-[11px] text-ink-3 mt-0.5">{activity.timestamp}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
