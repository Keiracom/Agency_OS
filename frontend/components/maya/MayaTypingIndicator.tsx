'use client';

/**
 * MayaTypingIndicator - Animated typing dots
 * Sprint 4: Maya Overlay Component
 * Bloomberg Terminal aesthetic - amber only
 */

import { cn } from '@/lib/utils';

interface MayaTypingIndicatorProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function MayaTypingIndicator({ 
  className,
  size = 'md' 
}: MayaTypingIndicatorProps) {
  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5'
  };

  const gaps = {
    sm: 'gap-1',
    md: 'gap-1.5',
    lg: 'gap-2'
  };

  return (
    <div className={cn('flex items-center', gaps[size], className)}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={cn(
            'rounded-full bg-[#D4956A]',
            dotSizes[size]
          )}
          style={{
            animation: `maya-typing-bounce 1.4s ease-in-out ${i * 0.16}s infinite`,
          }}
        />
      ))}
      <style jsx>{`
        @keyframes maya-typing-bounce {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.4;
          }
          30% {
            transform: translateY(-4px);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
