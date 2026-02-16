'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  accentTop?: boolean;
}

/**
 * GlassCard - Thick Glass Effect Component
 * 
 * Implements "physical frosted glass" aesthetic:
 * 1. TOP REFLECTION - overhead light gradient
 * 2. INNER DEPTH - bottom inner shadow for thickness
 * 3. EDGE HIGHLIGHT - gradient border (light source top-left)
 * 4. SUBTLE COLOR SHIFT - purple-blue refraction gradient
 * 5. FROSTED BLUR - backdrop-filter for frosted glass
 */
export function GlassCard({ children, className, glow, accentTop }: GlassCardProps) {
  return (
    <div
      className={cn(
        'glass-card relative rounded-2xl p-6 transition-all duration-200',
        glow && 'glass-card-glow',
        className
      )}
    >
      {/* Top reflection overlay */}
      <div 
        className="absolute inset-0 rounded-2xl pointer-events-none"
        style={{
          background: 'linear-gradient(180deg, rgba(255,255,255,0.07) 0%, transparent 30%)',
        }}
      />
      
      {/* Accent top line (optional) */}
      {accentTop && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-accent-primary to-accent-blue rounded-t-2xl z-10" />
      )}
      
      {/* Content */}
      <div className="relative z-[1]">
        {children}
      </div>
      
      <style jsx>{`
        .glass-card {
          /* Base background with color refraction gradient */
          background: 
            linear-gradient(135deg, rgba(124,58,237,0.03), rgba(59,130,246,0.03)),
            rgba(23, 22, 34, 0.7);
          
          /* Frosted glass blur */
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          
          /* Multi-layer shadow for depth + inner thickness */
          box-shadow: 
            /* Outer shadow - depth */
            0 12px 40px rgba(0, 0, 0, 0.5),
            0 2px 8px rgba(0, 0, 0, 0.3),
            /* Top inner highlight - light from above */
            inset 0 1px 0 rgba(255, 255, 255, 0.08),
            /* Bottom inner shadow - glass thickness */
            inset 0 -2px 6px rgba(0, 0, 0, 0.2);
          
          /* Gradient border effect using pseudo-element */
          border: 1px solid transparent;
          background-clip: padding-box;
          position: relative;
        }
        
        .glass-card::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: inherit;
          padding: 1px;
          background: linear-gradient(
            135deg,
            rgba(255, 255, 255, 0.12) 0%,
            rgba(255, 255, 255, 0.06) 50%,
            rgba(255, 255, 255, 0.02) 100%
          );
          -webkit-mask: 
            linear-gradient(#fff 0 0) content-box, 
            linear-gradient(#fff 0 0);
          mask: 
            linear-gradient(#fff 0 0) content-box, 
            linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none;
        }
        
        .glass-card:hover::before {
          background: linear-gradient(
            135deg,
            rgba(255, 255, 255, 0.18) 0%,
            rgba(255, 255, 255, 0.09) 50%,
            rgba(255, 255, 255, 0.03) 100%
          );
        }
        
        .glass-card-glow:hover {
          box-shadow: 
            0 12px 40px rgba(0, 0, 0, 0.5),
            0 2px 8px rgba(0, 0, 0, 0.3),
            0 0 20px rgba(124, 58, 237, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.08),
            inset 0 -2px 6px rgba(0, 0, 0, 0.2);
        }
      `}</style>
    </div>
  );
}
