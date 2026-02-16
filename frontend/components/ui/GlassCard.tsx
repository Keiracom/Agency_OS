'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

type GlassCardVariant = 'default' | 'accent';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  variant?: GlassCardVariant;
  glow?: boolean;
  accentTop?: boolean;
  hover?: boolean;
}

/**
 * GlassCard - Pure Bloomberg Glassmorphism
 * CEO Directive #027 — Design System Overhaul
 * 
 * Variants:
 * - "default": Standard frosted glass (white tints)
 * - "accent": Amber-tinted glass for hero metrics (Meetings Booked, etc.)
 * 
 * Features:
 * - Frosted glass background with blur(20px)
 * - Gradient borders (light source top-left)
 * - Inner glow on top edge
 * - Optional amber glow on hover
 */
export function GlassCard({ 
  children, 
  className, 
  variant = 'default',
  glow = false, 
  accentTop = false,
  hover = true 
}: GlassCardProps) {
  const isAccent = variant === 'accent';
  
  return (
    <div
      className={cn(
        'relative rounded-xl p-6 transition-all duration-200',
        isAccent ? 'glass-card-accent' : 'glass-card-default',
        hover && (isAccent ? 'glass-card-accent-hover' : 'glass-card-default-hover'),
        glow && 'glass-card-glow',
        className
      )}
    >
      {/* Top edge light refraction */}
      <div 
        className="absolute inset-x-0 top-0 h-px rounded-t-xl pointer-events-none"
        style={{
          background: isAccent
            ? 'linear-gradient(90deg, transparent 0%, rgba(212,149,106,0.25) 20%, rgba(212,149,106,0.25) 80%, transparent 100%)'
            : 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 20%, rgba(255,255,255,0.15) 80%, transparent 100%)',
        }}
      />
      
      {/* Left edge light refraction */}
      <div 
        className="absolute inset-y-0 left-0 w-px rounded-l-xl pointer-events-none"
        style={{
          background: isAccent
            ? 'linear-gradient(180deg, rgba(212,149,106,0.20) 0%, rgba(212,149,106,0.06) 100%)'
            : 'linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.04) 100%)',
        }}
      />
      
      {/* Accent top line (optional amber bar) */}
      {accentTop && (
        <div 
          className="absolute top-0 left-4 right-4 h-0.5 rounded-full z-10"
          style={{
            background: 'linear-gradient(90deg, transparent 0%, #D4956A 30%, #E8B48A 50%, #D4956A 70%, transparent 100%)',
          }}
        />
      )}
      
      {/* Content */}
      <div className="relative z-[1]">
        {children}
      </div>
      
      <style jsx>{`
        /* Default Glass Card */
        .glass-card-default {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.10);
          border-top-color: rgba(255,255,255,0.15);
          border-left-color: rgba(255,255,255,0.12);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow: 
            0 4px 24px rgba(0,0,0,0.3),
            inset 0 1px 0 rgba(255,255,255,0.06);
        }
        
        .glass-card-default-hover:hover {
          background: rgba(255,255,255,0.06);
          border-color: rgba(255,255,255,0.15);
          box-shadow: 
            0 8px 32px rgba(0,0,0,0.35),
            inset 0 1px 0 rgba(255,255,255,0.08);
        }
        
        /* Accent Glass Card (for hero metrics) */
        .glass-card-accent {
          background: rgba(212,149,106,0.06);
          border: 1px solid rgba(212,149,106,0.15);
          border-top-color: rgba(212,149,106,0.20);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow: 
            0 4px 24px rgba(0,0,0,0.3),
            0 0 40px rgba(212,149,106,0.03),
            inset 0 1px 0 rgba(212,149,106,0.08);
        }
        
        .glass-card-accent-hover:hover {
          background: rgba(212,149,106,0.08);
          border-color: rgba(212,149,106,0.20);
          box-shadow: 
            0 8px 32px rgba(0,0,0,0.35),
            0 0 48px rgba(212,149,106,0.06),
            inset 0 1px 0 rgba(212,149,106,0.12);
        }
        
        /* Glow effect (works with both variants) */
        .glass-card-glow:hover {
          box-shadow: 
            0 8px 32px rgba(0,0,0,0.35),
            0 0 24px rgba(212,149,106,0.15),
            inset 0 1px 0 rgba(255,255,255,0.08);
        }
      `}</style>
    </div>
  );
}

/**
 * GlassCardCompact - Smaller padding variant
 */
export function GlassCardCompact({ 
  children, 
  className,
  variant = 'default',
  glow = false,
  hover = true 
}: Omit<GlassCardProps, 'accentTop'>) {
  return (
    <GlassCard 
      className={cn('p-4', className)} 
      variant={variant}
      glow={glow}
      hover={hover}
    >
      {children}
    </GlassCard>
  );
}

/**
 * GlassPanel - Full-width glass panel (no border-radius on sides)
 */
export function GlassPanel({ 
  children, 
  className,
  variant = 'default'
}: { 
  children: ReactNode; 
  className?: string;
  variant?: GlassCardVariant;
}) {
  const isAccent = variant === 'accent';
  
  return (
    <div
      className={cn(
        'relative p-6',
        className
      )}
      style={{
        background: isAccent ? 'rgba(212,149,106,0.06)' : 'rgba(255,255,255,0.04)',
        borderTop: `1px solid ${isAccent ? 'rgba(212,149,106,0.15)' : 'rgba(255,255,255,0.10)'}`,
        borderBottom: `1px solid ${isAccent ? 'rgba(212,149,106,0.08)' : 'rgba(255,255,255,0.06)'}`,
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      {children}
    </div>
  );
}

/**
 * HeroMetricCard - Pre-configured accent card for key metrics
 * Use for: Meetings Booked, Revenue, Hot Leads, etc.
 */
export function HeroMetricCard({
  children,
  className,
  glow = true,
}: {
  children: ReactNode;
  className?: string;
  glow?: boolean;
}) {
  return (
    <GlassCard
      variant="accent"
      glow={glow}
      hover={true}
      className={className}
    >
      {children}
    </GlassCard>
  );
}
