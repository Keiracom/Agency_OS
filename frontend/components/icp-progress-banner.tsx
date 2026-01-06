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
        isRunning && 'bg-blue-50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800',
        isCompleted && 'bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800',
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
                <Loader2 className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-blue-900 dark:text-blue-100">
                    Setting up your profile...
                  </p>
                  {status.current_step && (
                    <p className="text-sm text-blue-700 dark:text-blue-300 truncate">
                      {status.current_step}
                    </p>
                  )}
                </div>
                <span className="text-sm font-medium text-blue-700 dark:text-blue-300 flex-shrink-0">
                  {Math.round(status.progress_percent)}%
                </span>
              </div>
              <Progress
                value={status.progress_percent}
                className="h-2 bg-blue-100 dark:bg-blue-900"
              />
            </div>
          )}

          {/* Completed State */}
          {isCompleted && (
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <p className="font-medium text-green-900 dark:text-green-100 flex-1">
                Your ICP is ready!
              </p>
              <Button
                size="sm"
                variant="ghost"
                onClick={onReview}
                className="text-green-700 hover:text-green-800 hover:bg-green-100 dark:text-green-300 dark:hover:bg-green-900/50 flex-shrink-0"
              >
                Review Now
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Failed State */}
          {isFailed && (
            <div className="flex items-center gap-3">
              <XCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-red-900 dark:text-red-100">
                  Couldn&apos;t analyze your website
                </p>
                {status.error_message && (
                  <p className="text-sm text-red-700 dark:text-red-300 truncate">
                    {status.error_message}
                  </p>
                )}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={onRetry}
                className="text-red-700 hover:text-red-800 hover:bg-red-100 dark:text-red-300 dark:hover:bg-red-900/50 flex-shrink-0"
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
            isRunning && 'text-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900/50',
            isCompleted && 'text-green-500 hover:bg-green-100 dark:hover:bg-green-900/50',
            isFailed && 'text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50'
          )}
          aria-label="Dismiss banner"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
