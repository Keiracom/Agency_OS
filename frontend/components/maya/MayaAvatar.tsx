'use client';

/**
 * MayaAvatar - Glowing amber ring with avatar placeholder
 * Sprint 4: Maya Overlay Component
 * HeyGen-ready: avatarSrc prop will accept video feed URL post-launch
 */

import { cn } from '@/lib/utils';
import { User } from 'lucide-react';

interface MayaAvatarProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  isPulsing?: boolean;
  avatarSrc?: string;
  avatarFallback?: 'silhouette' | 'initial' | 'icon';
  className?: string;
}

const sizes = {
  sm: {
    container: 'w-12 h-12',
    inner: 'w-10 h-10',
    ring: 2,
    text: 'text-lg',
    icon: 'w-5 h-5',
  },
  md: {
    container: 'w-20 h-20',
    inner: 'w-16 h-16',
    ring: 3,
    text: 'text-2xl',
    icon: 'w-8 h-8',
  },
  lg: {
    container: 'w-28 h-28',
    inner: 'w-24 h-24',
    ring: 4,
    text: 'text-4xl',
    icon: 'w-12 h-12',
  },
  xl: {
    container: 'w-36 h-36',
    inner: 'w-32 h-32',
    ring: 5,
    text: 'text-5xl',
    icon: 'w-16 h-16',
  },
};

export function MayaAvatar({
  size = 'lg',
  isPulsing = true,
  avatarSrc,
  avatarFallback = 'initial',
  className,
}: MayaAvatarProps) {
  const s = sizes[size];

  const renderFallback = () => {
    switch (avatarFallback) {
      case 'silhouette':
        return (
          <div className="relative w-full h-full flex items-center justify-center">
            <User 
              className={cn(s.icon, 'text-[#6B6660]')} 
              strokeWidth={1.5}
            />
          </div>
        );
      case 'icon':
        return (
          <div className="relative w-full h-full flex items-center justify-center">
            <div 
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, rgba(212,149,106,0.2) 0%, rgba(232,180,138,0.2) 100%)',
              }}
            >
              <span className="text-[#D4956A] font-semibold text-sm">AI</span>
            </div>
          </div>
        );
      case 'initial':
      default:
        return (
          <span 
            className={cn(
              'font-serif font-semibold',
              s.text
            )}
            style={{
              background: 'linear-gradient(135deg, #D4956A 0%, #E8B48A 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            M
          </span>
        );
    }
  };

  return (
    <div 
      className={cn(
        'relative flex items-center justify-center rounded-full',
        s.container,
        isPulsing && 'maya-avatar-pulse',
        className
      )}
    >
      {/* Outer glowing ring */}
      <div 
        className="absolute inset-0 rounded-full"
        style={{
          background: 'linear-gradient(135deg, #D4956A 0%, #E8B48A 50%, #D4956A 100%)',
          padding: `${s.ring}px`,
        }}
      >
        <div 
          className="w-full h-full rounded-full"
          style={{ backgroundColor: '#0C0A08' }}
        />
      </div>

      {/* Inner circle with avatar/placeholder */}
      <div 
        className={cn(
          'relative rounded-full flex items-center justify-center overflow-hidden',
          s.inner
        )}
        style={{
          backgroundColor: '#141210',
          border: '1px solid rgba(212,149,106,0.2)',
        }}
      >
        {avatarSrc ? (
          // HeyGen video feed will go here post-launch
          <video
            src={avatarSrc}
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover"
          />
        ) : (
          renderFallback()
        )}
      </div>

      {/* Glow effect layer */}
      <div 
        className="absolute inset-0 rounded-full pointer-events-none"
        style={{
          boxShadow: isPulsing 
            ? '0 0 30px rgba(212,149,106,0.3), 0 0 60px rgba(212,149,106,0.15)'
            : '0 0 20px rgba(212,149,106,0.2)',
        }}
      />

      <style jsx>{`
        .maya-avatar-pulse {
          animation: maya-ring-pulse 2s ease-in-out infinite;
        }

        @keyframes maya-ring-pulse {
          0%, 100% {
            filter: brightness(1);
          }
          50% {
            filter: brightness(1.15);
          }
        }

        .maya-avatar-pulse::before {
          content: '';
          position: absolute;
          inset: -4px;
          border-radius: 9999px;
          background: linear-gradient(135deg, rgba(212,149,106,0.4), rgba(232,180,138,0.2));
          opacity: 0;
          animation: maya-glow-expand 2s ease-in-out infinite;
        }

        @keyframes maya-glow-expand {
          0%, 100% {
            opacity: 0;
            transform: scale(0.95);
          }
          50% {
            opacity: 0.6;
            transform: scale(1.02);
          }
        }
      `}</style>
    </div>
  );
}
