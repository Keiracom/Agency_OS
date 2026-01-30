'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  href?: string;
}

export function Card({ children, className, onClick, href }: CardProps) {
  const Component = href ? 'a' : onClick ? 'button' : 'div';
  
  return (
    <Component
      href={href}
      onClick={onClick}
      className={cn(
        'bg-white rounded-xl shadow-sm border border-gray-100',
        'p-4 transition-all duration-200',
        onClick || href ? 'hover:shadow-md hover:border-gray-200 active:scale-[0.98] cursor-pointer' : '',
        className
      )}
    >
      {children}
    </Component>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: string;
  trend?: number;
  color?: 'default' | 'green' | 'blue' | 'yellow' | 'red' | 'purple';
}

const colorStyles = {
  default: 'bg-gray-50 text-gray-600',
  green: 'bg-green-50 text-green-600',
  blue: 'bg-blue-50 text-blue-600',
  yellow: 'bg-yellow-50 text-yellow-600',
  red: 'bg-red-50 text-red-600',
  purple: 'bg-purple-50 text-purple-600',
};

export function StatCard({ label, value, icon, trend, color = 'default' }: StatCardProps) {
  return (
    <Card className="flex items-center gap-4 min-h-[80px]">
      {icon && (
        <div className={cn('text-2xl p-3 rounded-xl', colorStyles[color])}>
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-500 truncate">{label}</p>
        <p className="text-2xl font-semibold text-gray-900 truncate">{value}</p>
        {trend !== undefined && (
          <p className={cn(
            'text-xs font-medium',
            trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'
          )}>
            {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {Math.abs(trend)}%
          </p>
        )}
      </div>
    </Card>
  );
}

interface ActivityCardProps {
  action: string;
  type: string;
  status: string;
  time: string;
  tokens?: number;
  onClick?: () => void;
}

export function ActivityCard({ action, type, status, time, tokens, onClick }: ActivityCardProps) {
  const typeIcons: Record<string, string> = {
    task: '📋',
    tool_call: '🔧',
    message: '💬',
    heartbeat: '💓',
    sync: '🔄',
    decision: '🧠',
    learning: '📚',
  };

  const statusColors: Record<string, string> = {
    completed: 'bg-green-500',
    running: 'bg-blue-500',
    pending: 'bg-yellow-500',
    failed: 'bg-red-500',
  };

  return (
    <Card onClick={onClick} className="flex items-start gap-3">
      <span className="text-xl mt-0.5">{typeIcons[type] || '📌'}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 line-clamp-2">{action}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className={cn('w-2 h-2 rounded-full', statusColors[status] || 'bg-gray-500')} />
          <span className="text-xs text-gray-500">{status}</span>
          <span className="text-xs text-gray-400">•</span>
          <span className="text-xs text-gray-500">{time}</span>
          {tokens !== undefined && tokens > 0 && (
            <>
              <span className="text-xs text-gray-400">•</span>
              <span className="text-xs text-gray-500">{tokens.toLocaleString()} tokens</span>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}

interface MemoryCardProps {
  title: string;
  content: string;
  category: string;
  importance?: number;
  time: string;
  onClick?: () => void;
}

export function MemoryCard({ title, content, category, importance, time, onClick }: MemoryCardProps) {
  const categoryColors: Record<string, string> = {
    general: 'bg-gray-100 text-gray-700',
    operational: 'bg-blue-100 text-blue-700',
    behavioral: 'bg-purple-100 text-purple-700',
    technical: 'bg-green-100 text-green-700',
    communication: 'bg-yellow-100 text-yellow-700',
    safety: 'bg-red-100 text-red-700',
  };

  return (
    <Card onClick={onClick} className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-medium text-gray-900 line-clamp-1">{title}</h3>
        <span className={cn(
          'text-xs px-2 py-1 rounded-full font-medium whitespace-nowrap',
          categoryColors[category] || 'bg-gray-100 text-gray-700'
        )}>
          {category}
        </span>
      </div>
      <p className="text-sm text-gray-600 line-clamp-3">{content}</p>
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>{time}</span>
        {importance && (
          <span className="flex items-center gap-1">
            {'⭐'.repeat(Math.min(importance, 5))}
          </span>
        )}
      </div>
    </Card>
  );
}
