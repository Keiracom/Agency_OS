'use client';

/**
 * MayaStatusBadge - Status text + animated progress
 * Sprint 4: Maya Overlay Component
 * Bloomberg Terminal aesthetic - amber only
 */

import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';

interface MayaStatusBadgeProps {
  status: string;
  progress?: number; // 0-100
  showProgress?: boolean;
  className?: string;
}

export function MayaStatusBadge({
  status,
  progress = 0,
  showProgress = true,
  className,
}: MayaStatusBadgeProps) {
  // Animate progress smoothly
  const [displayProgress, setDisplayProgress] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDisplayProgress(progress);
    }, 50);
    return () => clearTimeout(timer);
  }, [progress]);

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      {/* Status text with progress */}
      <div className="flex items-center gap-2">
        <span 
          className="text-xs font-mono font-semibold tracking-wider uppercase"
          style={{ color: '#D4956A' }}
        >
          {status}
        </span>
        {showProgress && progress > 0 && (
          <span 
            className="text-xs font-mono tabular-nums"
            style={{ color: '#E8B48A' }}
          >
            {Math.round(displayProgress)}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      {showProgress && progress > 0 && (
        <div 
          className="w-32 h-1 rounded-full overflow-hidden"
          style={{ backgroundColor: 'rgba(212,149,106,0.15)' }}
        >
          <div 
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${displayProgress}%`,
              background: 'linear-gradient(90deg, #D4956A 0%, #E8B48A 100%)',
            }}
          />
        </div>
      )}
    </div>
  );
}
