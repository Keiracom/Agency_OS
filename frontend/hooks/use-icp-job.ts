/**
 * FILE: frontend/hooks/use-icp-job.ts
 * PURPOSE: Hook for managing ICP extraction job state and polling
 * PHASE: 11 (ICP Discovery System)
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api, APIError } from '@/lib/api';
import type { ICPExtractionStatus } from '@/components/icp-progress-banner';
import type { ICPProfile } from '@/components/icp-review-modal';

const ICP_JOB_STORAGE_KEY = 'icp_job_id';
const POLL_INTERVAL = 3000; // 3 seconds

interface UseICPJobResult {
  // State
  jobId: string | null;
  status: ICPExtractionStatus | null;
  profile: ICPProfile | null;
  isLoading: boolean;
  error: string | null;

  // Derived state
  isRunning: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  showBanner: boolean;

  // Actions
  confirmICP: () => Promise<void>;
  dismissBanner: () => void;
  retryExtraction: () => void;
  clearJob: () => void;
}

export function useICPJob(): UseICPJobResult {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ICPExtractionStatus | null>(null);
  const [profile, setProfile] = useState<ICPProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const profileFetchedRef = useRef(false);

  // Initialize job ID from URL params or localStorage
  useEffect(() => {
    const urlJobId = searchParams.get('icp_job');
    const storedJobId = typeof window !== 'undefined'
      ? localStorage.getItem(ICP_JOB_STORAGE_KEY)
      : null;

    const activeJobId = urlJobId || storedJobId;

    if (activeJobId) {
      setJobId(activeJobId);

      // Store in localStorage if from URL
      if (urlJobId && typeof window !== 'undefined') {
        localStorage.setItem(ICP_JOB_STORAGE_KEY, urlJobId);
      }

      // Clean up URL by removing the icp_job parameter
      if (urlJobId) {
        const url = new URL(window.location.href);
        url.searchParams.delete('icp_job');
        router.replace(url.pathname + url.search, { scroll: false });
      }
    }
  }, [searchParams, router]);

  // Fetch status for a job
  const fetchStatus = useCallback(async (id: string): Promise<ICPExtractionStatus | null> => {
    try {
      const response = await api.get<ICPExtractionStatus>(
        `/api/v1/onboarding/status/${id}`
      );
      return response;
    } catch (err) {
      if (err instanceof APIError && err.status === 404) {
        // Job not found, clear it
        localStorage.removeItem(ICP_JOB_STORAGE_KEY);
        setJobId(null);
        return null;
      }
      throw err;
    }
  }, []);

  // Fetch profile result
  const fetchProfile = useCallback(async (id: string): Promise<ICPProfile | null> => {
    try {
      const response = await api.get<ICPProfile>(
        `/api/v1/onboarding/result/${id}`
      );
      return response;
    } catch (err) {
      if (err instanceof APIError && err.status === 202) {
        // Still in progress, return null
        return null;
      }
      throw err;
    }
  }, []);

  // Poll for status
  const poll = useCallback(async () => {
    if (!jobId) return;

    try {
      const statusData = await fetchStatus(jobId);
      if (!statusData) return;

      setStatus(statusData);
      setError(null);

      // If completed, fetch the profile (only once)
      if (statusData.status === 'completed' && !profileFetchedRef.current) {
        profileFetchedRef.current = true;
        const profileData = await fetchProfile(jobId);
        if (profileData) {
          setProfile(profileData);
        }
      }

      // Stop polling if completed or failed
      if (statusData.status === 'completed' || statusData.status === 'failed') {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (err) {
      console.error('[useICPJob] Poll error:', err);
      setError(err instanceof Error ? err.message : 'Failed to check status');
    }
  }, [jobId, fetchStatus, fetchProfile]);

  // Start polling when job ID changes
  useEffect(() => {
    if (!jobId) return;

    // Reset state for new job
    setDismissed(false);
    setProfile(null);
    setError(null);
    setIsLoading(true);
    profileFetchedRef.current = false;

    // Initial fetch
    poll().finally(() => setIsLoading(false));

    // Start polling
    pollIntervalRef.current = setInterval(poll, POLL_INTERVAL);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [jobId, poll]);

  // Confirm ICP
  const confirmICP = useCallback(async () => {
    if (!jobId) {
      throw new Error('No job ID');
    }

    await api.post('/api/v1/onboarding/confirm', { job_id: jobId });

    // Clear the job after confirmation
    localStorage.removeItem(ICP_JOB_STORAGE_KEY);
    setJobId(null);
    setStatus(null);
    setProfile(null);
    setDismissed(true);
  }, [jobId]);

  // Dismiss banner
  const dismissBanner = useCallback(() => {
    setDismissed(true);
  }, []);

  // Retry extraction (redirect to onboarding)
  const retryExtraction = useCallback(() => {
    // Clear current job
    localStorage.removeItem(ICP_JOB_STORAGE_KEY);
    setJobId(null);
    setStatus(null);
    setProfile(null);

    // Redirect to onboarding
    router.push('/onboarding');
  }, [router]);

  // Clear job completely
  const clearJob = useCallback(() => {
    localStorage.removeItem(ICP_JOB_STORAGE_KEY);
    setJobId(null);
    setStatus(null);
    setProfile(null);
    setDismissed(false);
  }, []);

  // Derived state
  const isRunning = status?.status === 'pending' || status?.status === 'running';
  const isCompleted = status?.status === 'completed';
  const isFailed = status?.status === 'failed';
  const showBanner = Boolean(jobId && status && !dismissed);

  return {
    jobId,
    status,
    profile,
    isLoading,
    error,
    isRunning,
    isCompleted,
    isFailed,
    showBanner,
    confirmICP,
    dismissBanner,
    retryExtraction,
    clearJob,
  };
}
