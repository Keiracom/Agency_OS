'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  accentTop?: boolean;
}

export function GlassCard({ children, className, glow, accentTop }: GlassCardProps) {
  return (
    <div
      className={cn(
        'relative rounded-2xl p-6 transition-all duration-200',
        'bg-glass-surface backdrop-blur-md',
        'border border-glass-border hover:border-glass-border-hover',
        'shadow-glass',
        glow && 'hover:shadow-glass-glow',
        className
      )}
    >
      {accentTop && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-accent-primary to-accent-blue rounded-t-2xl" />
      )}
      {children}
    </div>
  );
}
