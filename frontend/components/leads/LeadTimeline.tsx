'use client';

import { useState } from 'react';
import { TimelineEvent } from '@/data/mock-lead-detail';
import { Zap, Mail, Linkedin, MessageSquare, Phone, Database } from 'lucide-react';

interface LeadTimelineProps {
  events: TimelineEvent[];
  filters?: string[];
}

const channelIcons: Record<TimelineEvent['type'], React.ReactNode> = {
  email: <Mail className="w-4 h-4" />,
  linkedin: <Linkedin className="w-4 h-4" />,
  sms: <MessageSquare className="w-4 h-4" />,
  voice: <Phone className="w-4 h-4" />,
  enrichment: <Database className="w-4 h-4" />,
  reply: <Mail className="w-4 h-4" />,
};

const channelColors: Record<TimelineEvent['type'], string> = {
  email: 'border-channel-email bg-channel-email/15',
  linkedin: 'border-channel-linkedin bg-channel-linkedin/15',
  sms: 'border-channel-sms bg-channel-sms/15',
  voice: 'border-channel-voice bg-channel-voice/15',
  enrichment: 'border-accent-primary bg-accent-primary/15',
  reply: 'border-status-success bg-status-success/15',
};

const dotColors: Record<TimelineEvent['type'], string> = {
  email: 'border-channel-email bg-channel-email/20',
  linkedin: 'border-channel-linkedin bg-channel-linkedin/20',
  sms: 'border-channel-sms bg-channel-sms/20',
  voice: 'border-channel-voice bg-channel-voice/20',
  enrichment: 'border-accent-primary bg-accent-primary/20',
  reply: 'border-status-success bg-status-success/20',
};

const badgeStyles: Record<string, string> = {
  booked: 'bg-status-success/15 text-status-success',
  replied: 'bg-accent-blue/15 text-accent-blue',
  opened: 'bg-accent-primary/15 text-accent-primary',
  clicked: 'bg-accent-teal/15 text-accent-teal',
};

const filterTypes = ['all', 'email', 'linkedin', 'voice', 'sms'] as const;

export function LeadTimeline({ events, filters: initialFilters }: LeadTimelineProps) {
  const [activeFilter, setActiveFilter] = useState<string>(initialFilters?.[0] ?? 'all');

  // Filter events
  const filteredEvents =
    activeFilter === 'all'
      ? events
      : events.filter((e) => e.type === activeFilter || (activeFilter === 'email' && e.type === 'reply'));

  // Group events by date
  const groupedEvents = filteredEvents.reduce(
    (groups, event) => {
      const date = event.date;
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(event);
      return groups;
    },
    {} as Record<string, TimelineEvent[]>
  );

  const dateOrder = Object.keys(groupedEvents);

  return (
    <div className="bg-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Zap className="w-4 h-4 text-accent-primary" />
          <span className="text-sm font-semibold text-primary">Activity Timeline</span>
        </div>
        <span className="text-xs text-muted">Multi-channel engagement history</span>
      </div>

      <div className="p-6">
        {/* Filter buttons */}
        <div className="flex gap-2 mb-5">
          {filterTypes.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors capitalize ${
                activeFilter === filter
                  ? 'bg-surface-hover text-primary border-border-strong'
                  : 'bg-elevated text-muted border-border-default hover:text-secondary'
              }`}
            >
              {filter === 'all' ? (
                'All'
              ) : (
                <span className="flex items-center gap-1.5">
                  {channelIcons[filter as TimelineEvent['type']]}
                  {filter}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Timeline list */}
        <div className="space-y-6">
          {dateOrder.map((date) => (
            <div key={date} className="timeline-day">
              {/* Date header */}
              <div
                className={`flex items-center gap-3 text-xs font-semibold uppercase tracking-wider mb-3 ${
                  date === 'Today' ? 'text-status-success' : 'text-muted'
                }`}
              >
                {date}
                <div className="flex-1 h-px bg-border-subtle" />
              </div>

              {/* Events */}
              <div className="flex flex-col gap-2 pl-5 border-l-2 border-border-subtle">
                {groupedEvents[date].map((event) => (
                  <div
                    key={event.id}
                    className="relative flex items-start gap-3.5 p-3.5 bg-surface-hover rounded-lg cursor-pointer hover:bg-elevated hover:translate-x-1 transition-all"
                  >
                    {/* Timeline dot */}
                    <div
                      className={`absolute -left-[1.625rem] top-4 w-2.5 h-2.5 rounded-full border-2 ${dotColors[event.type]}`}
                    />

                    {/* Icon */}
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${channelColors[event.type]}`}
                    >
                      {channelIcons[event.type]}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-primary font-medium">{event.title}</span>
                        {event.badge && (
                          <span
                            className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${badgeStyles[event.badge]}`}
                          >
                            {event.badge}
                          </span>
                        )}
                      </div>
                      {event.detail && (
                        <p className="text-sm text-secondary mt-1 line-clamp-2">{event.detail}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-muted font-mono">{event.time}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {filteredEvents.length === 0 && (
            <div className="text-center py-8 text-muted text-sm">
              No activity found for this filter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
