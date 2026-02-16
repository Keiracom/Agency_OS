/**
 * FILE: frontend/components/inbox/detail/QuickActions.tsx
 * PURPOSE: Sidebar action buttons
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { Calendar, Edit3, Upload, User } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickAction {
  icon: typeof Calendar;
  label: string;
  primary?: boolean;
  onClick?: () => void;
}

const actions: QuickAction[] = [
  { icon: Calendar, label: 'Schedule Call', primary: true },
  { icon: Edit3, label: 'Add Note' },
  { icon: Upload, label: 'Send to CRM' },
  { icon: User, label: 'View Full Profile' },
];

interface QuickActionsProps {
  onScheduleCall?: () => void;
  onAddNote?: () => void;
  onSendToCRM?: () => void;
  onViewProfile?: () => void;
}

export function QuickActions({ onScheduleCall, onAddNote, onSendToCRM, onViewProfile }: QuickActionsProps) {
  const handlers = [onScheduleCall, onAddNote, onSendToCRM, onViewProfile];
  
  return (
    <div className="bg-bg-base rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-text-muted">
        <span className="text-amber-500"></span>
        Quick Actions
      </div>
      <div className="space-y-2">
        {actions.map((action, index) => (
          <button
            key={action.label}
            onClick={handlers[index]}
            className={cn(
              'w-full flex items-center gap-3 px-3.5 py-3 rounded-lg text-sm font-medium transition-all',
              action.primary
                ? 'bg-amber-600 text-text-primary hover:bg-amber-500'
                : 'glass-surface border border-border-subtle text-text-primary hover:bg-bg-surface/[0.05] hover:translate-x-0.5'
            )}
          >
            <action.icon className={cn('w-[18px] h-[18px]', action.primary ? 'text-text-primary/80' : 'text-text-muted')} />
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
