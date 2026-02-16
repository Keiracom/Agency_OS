'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  accentTop?: boolean;
  hover?: boolean;
}

/**
 * GlassCard - Pure Bloomberg Glassmorphism
 * 
 * Implements aggressive frosted glass with visible depth:
 * - Frosted glass background with blur
 * - Gradient borders (light source top-left)
 * - Inner glow on top edge
 * - Optional amber glow on hover
 * 
 * CEO Directive #027 — Design System Overhaul
 */
export function GlassCard({ 
  children, 
  className, 
  glow = false, 
  accentTop = false,
  hover = true 
}: GlassCardProps) {
  return (
    <div
      className={cn(
        'glass-card relative rounded-xl p-6',
        hover && 'glass-card-hover',
        glow && 'glass-card-glow',
        className
      )}
    >
      {/* Top edge light refraction */}
      <div 
        className="absolute inset-x-0 top-0 h-px rounded-t-xl pointer-events-none"
        style={{
          background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 20%, rgba(255,255,255,0.15) 80%, transparent 100%)',
        }}
      />
      
      {/* Left edge light refraction */}
      <div 
        className="absolute inset-y-0 left-0 w-px rounded-l-xl pointer-events-none"
        style={{
          background: 'linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.04) 100%)',
        }}
      />
      
      {/* Accent top line (optional amber) */}
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
        .glass-card {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.10);
          border-top-color: rgba(255,255,255,0.15);
          border-left-color: rgba(255,255,255,0.12);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow: 
            0 4px 24px rgba(0,0,0,0.3),
            inset 0 1px 0 rgba(255,255,255,0.06);
          transition: all 0.2s ease;
        }
        
        .glass-card-hover:hover {
          background: rgba(255,255,255,0.06);
          border-color: rgba(255,255,255,0.15);
          box-shadow: 
            0 8px 32px rgba(0,0,0,0.35),
            inset 0 1px 0 rgba(255,255,255,0.08);
        }
        
        .glass-card-glow:hover {
          box-shadow: 
            0 8px 32px rgba(0,0,0,0.35),
            0 0 24px rgba(212,149,106,0.12),
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
  glow = false,
  hover = true 
}: Omit<GlassCardProps, 'accentTop'>) {
  return (
    <GlassCard 
      className={cn('p-4', className)} 
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
  className 
}: { 
  children: ReactNode; 
  className?: string;
}) {
  return (
    <div
      className={cn(
        'relative p-6',
        className
      )}
      style={{
        background: 'rgba(255,255,255,0.04)',
        borderTop: '1px solid rgba(255,255,255,0.10)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      {children}
    </div>
  );
}
