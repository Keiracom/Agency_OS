/**
 * FILE: frontend/components/icp-progress-banner.tsx
 * PURPOSE: Progress banner for ICP extraction shown on dashboard
 * PHASE: 11 (ICP Discovery System)
 */

'use client';

import { X, Loader2, CheckCircle2, XCircle, ArrowRight, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

export type ICPJobStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ICPExtractionStatus {
  job_id: string;
  status: ICPJobStatus;
  current_step: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  error_message: string | null;
}

interface ICPProgressBannerProps {
  status: ICPExtractionStatus;
  onReview: () => void;
  onRetry: () => void;
  onDismiss: () => void;
  className?: string;
}

export function ICPProgressBanner({
  status,
  onReview,
  onRetry,
  onDismiss,
  className,
}: ICPProgressBannerProps) {
  const isRunning = status.status === 'pending' || status.status === 'running';
  const isCompleted = status.status === 'completed';
  const isFailed = status.status === 'failed';

  // Don't render if status is unknown
  if (!isRunning && !isCompleted && !isFailed) {
    return null;
  }

  return (
    <div
      className={cn(
        'relative rounded-lg border p-4 shadow-sm transition-all duration-300',
        isRunning && 'bg-bg-surface border-blue-200 dark:bg-blue-950/30 dark:border-blue-800',
        isCompleted && 'bg-amber-glow border-amber dark:bg-amber-glow dark:border-amber',
        isFailed && 'bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Running/Pending State */}
          {isRunning && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-text-secondary dark:text-text-secondary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-bg-void dark:text-amber-glow">
                    Setting up your profile...
                  </p>
                  {status.current_step && (
                    <p className="text-sm text-amber dark:text-amber-light truncate">
                      {status.current_step}
                    </p>
                  )}
                </div>
                <span className="text-sm font-medium text-amber dark:text-amber-light flex-shrink-0">
                  {Math.round(status.progress_percent)}%
                </span>
              </div>
              <Progress
                value={status.progress_percent}
                className="h-2 bg-amber-glow dark:bg-bg-void"
              />
            </div>
          )}

          {/* Completed State */}
          {isCompleted && (
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-amber dark:text-amber flex-shrink-0" />
              <p className="font-medium text-amber dark:text-amber-glow flex-1">
                Your ICP is ready!
              </p>
              <Button
                size="sm"
                variant="ghost"
                onClick={onReview}
                className="text-amber hover:text-amber hover:bg-amber-glow dark:text-amber-light dark:hover:bg-amber-glow flex-shrink-0"
              >
                Review Now
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Failed State */}
          {isFailed && (
            <div className="flex items-center gap-3">
              <XCircle className="h-5 w-5 text-amber dark:text-amber flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-error dark:text-amber-glow">
                  Couldn&apos;t analyze your website
                </p>
                {status.error_message && (
                  <p className="text-sm text-error dark:text-amber-light truncate">
                    {status.error_message}
                  </p>
                )}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={onRetry}
                className="text-error hover:text-error hover:bg-amber-glow dark:text-amber-light dark:hover:bg-error-glow flex-shrink-0"
              >
                <RefreshCw className="mr-1 h-4 w-4" />
                Try Again
              </Button>
            </div>
          )}
        </div>

        {/* Dismiss button */}
        <button
          onClick={onDismiss}
          className={cn(
            'rounded-md p-1 transition-colors flex-shrink-0',
            isRunning && 'text-text-secondary hover:bg-amber-glow dark:hover:bg-bg-void/50',
            isCompleted && 'text-amber hover:bg-amber-glow dark:hover:bg-amber-glow',
            isFailed && 'text-amber hover:bg-amber-glow dark:hover:bg-red-900/50'
          )}
          aria-label="Dismiss banner"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
