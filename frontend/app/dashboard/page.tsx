/**
 * FILE: frontend/app/dashboard/page.tsx
 * PURPOSE: Dashboard V4 - Outcome-focused, customer-centric dashboard
 * PHASE: Dashboard V4 Implementation
 * 
 * Features:
 * - Celebration banner (conditional) - Shows when targets hit early
 * - Meetings vs Goal - Hero metric with gauge visualization
 * - Momentum indicator - Trending vs last month
 * - 4 quick stats - Show rate, deals started, pipeline value, ROI
 * - Hot Right Now - 3-5 prospects showing buying signals
 * - Week Ahead - Upcoming meetings with deal values
 * - What's Working - ONE simple insight
 * - Warm Replies - Actionable opportunities
 */

"use client";

import { Suspense } from "react";
import { AnimatePresence } from "framer-motion";
import { useDashboardV4 } from "@/hooks/use-dashboard-v4";
import { useICPJob } from "@/hooks/use-icp-job";
import { ICPProgressBanner } from "@/components/icp-progress-banner";
import { ICPReviewModal } from "@/components/icp-review-modal";
import { Skeleton } from "@/components/ui/loading-skeleton";
import { useState } from "react";

import {
  CelebrationBanner,
  HeroMeetingsCard,
  QuickStatsRow,
  HotProspectsCard,
  WeekAheadCard,
  InsightCard,
  WarmRepliesCard,
} from "@/components/dashboard-v4";

function DashboardV4Content() {
  const { data, isLoading, error } = useDashboardV4();

  // ICP extraction job state (keep for onboarding flow)
  const {
    status: icpStatus,
    profile: icpProfile,
    showBanner,
    confirmICP,
    dismissBanner,
    retryExtraction,
  } = useICPJob();

  const [showReviewModal, setShowReviewModal] = useState(false);

  const handleReview = () => {
    setShowReviewModal(true);
  };

  const handleConfirmICP = async () => {
    await confirmICP();
    setShowReviewModal(false);
  };

  if (isLoading) {
    return <DashboardV4Skeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">
          Unable to load dashboard. Please try refreshing.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* ICP Progress Banner (onboarding) */}
      {showBanner && icpStatus && (
        <ICPProgressBanner
          status={icpStatus}
          onReview={handleReview}
          onRetry={retryExtraction}
          onDismiss={dismissBanner}
        />
      )}

      {/* ICP Review Modal */}
      <ICPReviewModal
        open={showReviewModal}
        onOpenChange={setShowReviewModal}
        profile={icpProfile}
        onConfirm={handleConfirmICP}
        onStartOver={retryExtraction}
      />

      {/* Page Header */}
      <header>
        <h1 className="text-3xl font-bold tracking-tight">{data.greeting}</h1>
        <p className="text-muted-foreground">{data.subtext}</p>
      </header>

      {/* Celebration Banner (conditional) */}
      <AnimatePresence>
        {data.celebration?.show && (
          <CelebrationBanner
            title={data.celebration.title}
            subtitle={data.celebration.subtitle}
          />
        )}
      </AnimatePresence>

      {/* Hero: Meetings vs Goal */}
      <HeroMeetingsCard
        meetingsGoal={data.meetingsGoal}
        momentum={data.momentum}
      />

      {/* Quick Stats Row */}
      <QuickStatsRow stats={data.quickStats} />

      {/* Two Column Grid: Hot Prospects + Week Ahead */}
      <div className="grid gap-6 lg:grid-cols-2">
        <HotProspectsCard prospects={data.hotProspects} />
        <WeekAheadCard meetings={data.weekAhead} />
      </div>

      {/* Two Column Grid: Insight + Warm Replies */}
      <div className="grid gap-6 lg:grid-cols-2">
        <InsightCard insight={data.insight} />
        <WarmRepliesCard replies={data.warmReplies} />
      </div>
    </div>
  );
}

function DashboardV4Skeleton() {
  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header skeleton */}
      <div>
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-5 w-96 mt-2" />
      </div>

      {/* Hero card skeleton */}
      <Skeleton className="h-48 w-full rounded-xl" />

      {/* Quick stats skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
        ))}
      </div>

      {/* Two column grid skeleton */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-72 w-full rounded-xl" />
        <Skeleton className="h-72 w-full rounded-xl" />
      </div>

      {/* Bottom grid skeleton */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardV4Skeleton />}>
      <DashboardV4Content />
    </Suspense>
  );
}
