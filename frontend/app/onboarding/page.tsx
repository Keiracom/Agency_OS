"use client";

/**
 * FILE: frontend/app/onboarding/page.tsx
 * PURPOSE: Agency onboarding flow - website URL + integrations + ICP review
 * SPRINT: Dashboard Sprint 1 - Onboarding Port
 * SSOT: frontend/design/html-prototypes/onboarding-v3.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 *
 * ARCHITECTURE DECISION: LinkedIn and CRM connections are MANDATORY
 * - Cannot proceed to dashboard without both connections
 * - Clear messaging about why each connection is required
 *
 * STEP 3/8: Wired to real backend APIs (no more setTimeout placeholders)
 * - HubSpot OAuth: GET /api/v1/crm/auth/hubspot
 * - LinkedIn OAuth: GET /api/v1/linkedin/connect
 * - ICP Extraction: POST /api/v1/onboarding/analyze
 * - Job Status: GET /api/v1/onboarding/status/{job_id}
 * - Job Result: GET /api/v1/onboarding/result/{job_id}
 * - ICP Confirm: POST /api/v1/onboarding/confirm
 * - Gate Check: GET /api/v1/onboarding/gates
 *
 * DIRECTIVE #183 — Added ICP review/confirm step (step 3)
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Check,
  Globe,
  Linkedin,
  ArrowRight,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Edit2,
  Target,
  MapPin,
  Users,
  Briefcase,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { MayaOverlay } from "@/components/maya";

type OnboardingStep = "website" | "integrations" | "icp_review" | "complete";
type JobStatus = "pending" | "running" | "completed" | "failed";

interface ICPExtractionStatus {
  job_id: string;
  status: JobStatus;
  current_step: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  error_message: string | null;
}

interface ICPProfile {
  company_name: string;
  website_url: string;
  company_description: string;
  services_offered: string[];
  value_proposition: string;
  icp_industries: string[];
  icp_company_sizes: string[];
  icp_revenue_ranges: string[];
  icp_locations: string[];
  icp_titles: string[];
  icp_pain_points: string[];
  confidence: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const POLL_INTERVAL_MS = 3000;

export default function OnboardingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [websiteValid, setWebsiteValid] = useState(false);
  const [hubspotConnected, setHubspotConnected] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("website");
  const [isLoading, setIsLoading] = useState(false);
  const [isHubspotLoading, setIsHubspotLoading] = useState(false);
  const [isLinkedinLoading, setIsLinkedinLoading] = useState(false);
  const [isMayaMinimised, setIsMayaMinimised] = useState(false);
  const [mayaProgress, setMayaProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // ICP review state
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ICPExtractionStatus | null>(null);
  const [icpProfile, setIcpProfile] = useState<ICPProfile | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedProfile, setEditedProfile] = useState<Partial<ICPProfile>>({});
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const profileFetchedRef = useRef(false);

  // Handle OAuth callbacks from query params
  useEffect(() => {
    const hubspotSuccess = searchParams.get("hubspot") === "connected";
    const linkedinSuccess = searchParams.get("linkedin") === "connected";
    const oauthError = searchParams.get("oauth_error");

    if (hubspotSuccess) {
      setHubspotConnected(true);
      setCurrentStep("integrations");
    }
    if (linkedinSuccess) {
      setLinkedinConnected(true);
      setCurrentStep("integrations");
    }
    if (oauthError) {
      setError(`OAuth failed: ${oauthError}`);
    }
  }, [searchParams]);

  // Validate website URL
  useEffect(() => {
    try {
      if (websiteUrl) {
        new URL(
          websiteUrl.startsWith("http") ? websiteUrl : `https://${websiteUrl}`
        );
        setWebsiteValid(true);
      } else {
        setWebsiteValid(false);
      }
    } catch {
      setWebsiteValid(false);
    }
  }, [websiteUrl]);

  // Update Maya progress based on step
  useEffect(() => {
    const progressMap: Record<OnboardingStep, number> = {
      website: 25,
      integrations: 50,
      icp_review: 75,
      complete: 100,
    };
    setMayaProgress(progressMap[currentStep] || 0);
  }, [currentStep]);

  // Poll job status when in icp_review step
  const fetchJobStatus = useCallback(async (id: string) => {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/status/${id}`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Status fetch failed (${res.status})`);
    return res.json() as Promise<ICPExtractionStatus>;
  }, []);

  const fetchJobResult = useCallback(async (id: string) => {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/result/${id}`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Result fetch failed (${res.status})`);
    return res.json() as Promise<ICPProfile>;
  }, []);

  useEffect(() => {
    if (currentStep !== "icp_review" || !jobId) return;

    const poll = async () => {
      try {
        const status = await fetchJobStatus(jobId);
        setJobStatus(status);

        if (status.status === "completed" && !profileFetchedRef.current) {
          profileFetchedRef.current = true;
          try {
            const profile = await fetchJobResult(jobId);
            setIcpProfile(profile);
            setEditedProfile({});
          } catch (err) {
            console.error("Result fetch error:", err);
          }
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        } else if (status.status === "failed") {
          setError(status.error_message ?? "ICP extraction failed");
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    };

    profileFetchedRef.current = false;
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [currentStep, jobId, fetchJobStatus, fetchJobResult]);

  const handleWebsiteSubmit = () => {
    if (websiteValid) setCurrentStep("integrations");
  };

  // HubSpot OAuth
  const handleHubspotConnect = useCallback(async () => {
    setError(null);
    setIsHubspotLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/crm/connect/hubspot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail ||
            errorData.message ||
            `HubSpot auth failed (${response.status})`
        );
      }
      const data = await response.json();
      if (data.oauth_url) {
        window.location.href = data.oauth_url;
      } else if (data.redirect_url || data.auth_url || data.url) {
        window.location.href = data.redirect_url || data.auth_url || data.url;
      } else {
        setHubspotConnected(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect HubSpot");
    } finally {
      setIsHubspotLoading(false);
    }
  }, []);

  // LinkedIn OAuth
  const handleLinkedinConnect = useCallback(async () => {
    setError(null);
    setIsLinkedinLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/linkedin/connect`, {
        method: "GET",
        credentials: "include",
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || `LinkedIn auth failed (${response.status})`
        );
      }
      const data = await response.json();
      if (
        data.redirect_url ||
        data.auth_url ||
        data.url ||
        data.hosted_auth_url
      ) {
        window.location.href =
          data.hosted_auth_url ||
          data.redirect_url ||
          data.auth_url ||
          data.url;
      } else {
        setLinkedinConnected(true);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect LinkedIn"
      );
    } finally {
      setIsLinkedinLoading(false);
    }
  }, []);

  // Launch → calls /analyze, transitions to icp_review
  const handleLaunch = useCallback(async () => {
    setError(null);
    setIsLoading(true);

    try {
      const normalizedUrl = websiteUrl.startsWith("http")
        ? websiteUrl
        : `https://${websiteUrl}`;

      const response = await fetch(`${API_BASE}/api/v1/onboarding/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          website_url: normalizedUrl,
          crm_connected: hubspotConnected,
          linkedin_connected: linkedinConnected,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || `Analysis failed (${response.status})`
        );
      }

      const data = await response.json();

      // Store job_id and move to ICP review step
      if (data.job_id) {
        setJobId(data.job_id);
        setCurrentStep("icp_review");
      } else {
        // Fallback if no job_id returned — go straight to dashboard
        router.push("/dashboard?onboarding=true");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to analyze website"
      );
    } finally {
      setIsLoading(false);
    }
  }, [websiteUrl, hubspotConnected, linkedinConnected, router]);

  // Confirm ICP → calls /confirm, then redirects
  const handleConfirmICP = useCallback(async () => {
    if (!jobId) return;
    setIsConfirming(true);
    setError(null);

    try {
      // Build adjustments from edited fields if in edit mode
      const adjustments =
        editMode && Object.keys(editedProfile).length > 0
          ? editedProfile
          : undefined;

      const response = await fetch(`${API_BASE}/api/v1/onboarding/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          job_id: jobId,
          adjustments: adjustments ?? null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail ||
            errorData.message ||
            `Confirm failed (${response.status})`
        );
      }

      setCurrentStep("complete");
      router.push("/dashboard?onboarding=true");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to confirm ICP");
    } finally {
      setIsConfirming(false);
    }
  }, [jobId, editMode, editedProfile, router]);

  const canLaunch = websiteValid && hubspotConnected && linkedinConnected;

  const mergedProfile = icpProfile
    ? { ...icpProfile, ...editedProfile }
    : null;

  const jobIsRunning =
    jobStatus?.status === "pending" || jobStatus?.status === "running";
  const jobIsCompleted = jobStatus?.status === "completed";

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{ backgroundColor: "#0C0A08" }}
    >
      <div className="w-full max-w-[520px]">
        {/* Logo Section */}
        <div className="text-center mb-10">
          <div className="w-14 h-14 mx-auto mb-5 rounded-2xl gradient-premium flex items-center justify-center shadow-glow-md">
            <Check className="w-7 h-7 text-text-primary" strokeWidth={3} />
          </div>
          <h1 className="text-3xl font-serif text-text-primary mb-2">
            Agency OS
          </h1>
          <p className="text-text-secondary text-sm">
            Your digital employee is ready to work
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div
            className="mb-6 rounded-xl p-4 flex items-start gap-3"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
            }}
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-400">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-xs text-red-300 hover:text-red-200 mt-1 underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* ─── STEP 3: ICP REVIEW ─── */}
        {currentStep === "icp_review" && (
          <div className="glass-surface rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-border-subtle">
              <div className="flex items-center justify-center mb-4">
                <span
                  className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold"
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(212, 149, 106, 0.15), rgba(224, 168, 125, 0.15))",
                    border: "1px solid rgba(212, 149, 106, 0.3)",
                    color: "#D4956A",
                  }}
                >
                  <Target className="w-3.5 h-3.5" />
                  Step 3 of 3 — Review Your ICP
                </span>
              </div>
              <h2 className="text-xl font-serif text-text-primary text-center">
                {jobIsRunning
                  ? "Analyzing your agency..."
                  : jobIsCompleted
                  ? "Your Ideal Client Profile"
                  : "Preparing results..."}
              </h2>
              <p className="text-text-secondary text-sm text-center mt-1">
                {jobIsRunning
                  ? `${jobStatus?.current_step ?? "Extracting ICP from your website"}...`
                  : "Review what we found and confirm before launching"}
              </p>
            </div>

            <div className="p-6">
              {/* Running State */}
              {jobIsRunning && (
                <div className="space-y-5">
                  <div className="flex items-center justify-center gap-3 py-4">
                    <Loader2 className="w-6 h-6 text-accent-primary animate-spin" />
                    <span className="text-sm text-text-secondary">
                      {jobStatus?.current_step ?? "Analyzing your website"}
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div
                    className="w-full h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${jobStatus?.progress_percent ?? 10}%`,
                        background:
                          "linear-gradient(90deg, #D4956A 0%, #E0A87D 100%)",
                      }}
                    />
                  </div>
                  <div className="space-y-2">
                    {[
                      "Scraping website content",
                      "Extracting industry signals",
                      "Building ICP profile",
                    ].map((step, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div
                          className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{
                            backgroundColor:
                              (jobStatus?.completed_steps ?? 0) > i
                                ? "rgba(16, 185, 129, 0.2)"
                                : "rgba(255,255,255,0.05)",
                          }}
                        >
                          {(jobStatus?.completed_steps ?? 0) > i ? (
                            <CheckCircle2 className="w-3 h-3 text-status-success" />
                          ) : (jobStatus?.completed_steps ?? 0) === i ? (
                            <Loader2 className="w-3 h-3 text-accent-primary animate-spin" />
                          ) : (
                            <div className="w-1.5 h-1.5 rounded-full bg-text-muted" />
                          )}
                        </div>
                        <span
                          className="text-xs"
                          style={{
                            color:
                              (jobStatus?.completed_steps ?? 0) > i
                                ? "#10B981"
                                : (jobStatus?.completed_steps ?? 0) === i
                                ? "#D4956A"
                                : "#6B6560",
                          }}
                        >
                          {step}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Completed — show ICP */}
              {jobIsCompleted && mergedProfile && (
                <div className="space-y-5">
                  {/* Edit toggle */}
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-text-muted">
                      Confidence:{" "}
                      <span className="text-accent-primary font-mono">
                        {Math.round((mergedProfile.confidence ?? 0) * 100)}%
                      </span>
                    </p>
                    <button
                      onClick={() => setEditMode(!editMode)}
                      className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
                    >
                      <Edit2 className="w-3 h-3" />
                      {editMode ? "Done editing" : "Edit fields"}
                    </button>
                  </div>

                  {/* ICP Grid */}
                  <div className="space-y-4">
                    {/* Industries */}
                    <ICPField
                      icon={<Briefcase className="w-4 h-4" />}
                      label="Target Industries"
                      values={mergedProfile.icp_industries ?? []}
                      editMode={editMode}
                      onEdit={(vals) =>
                        setEditedProfile((p) => ({
                          ...p,
                          icp_industries: vals,
                        }))
                      }
                    />
                    {/* Locations */}
                    <ICPField
                      icon={<MapPin className="w-4 h-4" />}
                      label="Target Geography"
                      values={mergedProfile.icp_locations ?? []}
                      editMode={editMode}
                      onEdit={(vals) =>
                        setEditedProfile((p) => ({
                          ...p,
                          icp_locations: vals,
                        }))
                      }
                    />
                    {/* Company sizes */}
                    <ICPField
                      icon={<Users className="w-4 h-4" />}
                      label="Company Size"
                      values={mergedProfile.icp_company_sizes ?? []}
                      editMode={editMode}
                      onEdit={(vals) =>
                        setEditedProfile((p) => ({
                          ...p,
                          icp_company_sizes: vals,
                        }))
                      }
                    />
                    {/* Titles */}
                    <ICPField
                      icon={<Target className="w-4 h-4" />}
                      label="Decision Maker Titles"
                      values={mergedProfile.icp_titles ?? []}
                      editMode={editMode}
                      onEdit={(vals) =>
                        setEditedProfile((p) => ({ ...p, icp_titles: vals }))
                      }
                    />
                  </div>

                  {/* Value prop */}
                  {mergedProfile.value_proposition && (
                    <div
                      className="rounded-xl p-4"
                      style={{
                        backgroundColor: "rgba(212, 149, 106, 0.06)",
                        border: "1px solid rgba(212, 149, 106, 0.2)",
                      }}
                    >
                      <p className="text-xs font-medium text-accent-primary mb-1">
                        Value Proposition
                      </p>
                      <p className="text-sm text-text-secondary">
                        {mergedProfile.value_proposition}
                      </p>
                    </div>
                  )}

                  {/* Confirm button */}
                  <button
                    onClick={handleConfirmICP}
                    disabled={isConfirming}
                    className="w-full py-4 rounded-xl text-[15px] font-semibold
                      transition-all duration-200 flex items-center justify-center gap-2
                      disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-glow-md"
                    style={{
                      background:
                        "linear-gradient(135deg, #D4956A 0%, #E0A87D 100%)",
                      color: "#0C0A08",
                    }}
                  >
                    {isConfirming ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Launching your dashboard...
                      </>
                    ) : (
                      <>
                        Looks good — Launch Dashboard
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setEditMode(true)}
                    className="w-full py-2.5 rounded-xl text-sm font-medium text-text-muted hover:text-text-secondary transition-colors"
                  >
                    Something looks off? Edit above ↑
                  </button>
                </div>
              )}

              {/* No profile yet but completed (should not happen) */}
              {jobIsCompleted && !mergedProfile && (
                <div className="text-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-accent-primary mx-auto mb-3" />
                  <p className="text-sm text-text-muted">Loading your ICP...</p>
                </div>
              )}

              {/* Failed state */}
              {jobStatus?.status === "failed" && (
                <div className="text-center py-8 space-y-4">
                  <p className="text-sm text-red-400">
                    {jobStatus.error_message ?? "Extraction failed"}
                  </p>
                  <button
                    onClick={() => {
                      setCurrentStep("integrations");
                      setJobId(null);
                      setJobStatus(null);
                    }}
                    className="text-sm text-accent-primary hover:underline"
                  >
                    ← Back to try again
                  </button>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-border-subtle">
              <p className="text-xs text-text-muted text-center">
                Need help?{" "}
                <a
                  href="mailto:support@agency-os.com"
                  className="text-accent-primary hover:underline"
                >
                  Contact support
                </a>
              </p>
            </div>
          </div>
        )}

        {/* ─── STEPS 1 & 2: website + integrations ─── */}
        {currentStep !== "icp_review" && currentStep !== "complete" && (
          <div className="glass-surface rounded-2xl overflow-hidden">
            {/* Card Header */}
            <div className="p-6 border-b border-border-subtle">
              <div className="flex items-center justify-center mb-4">
                <span
                  className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold"
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(212, 149, 106, 0.15), rgba(224, 168, 125, 0.15))",
                    border: "1px solid rgba(212, 149, 106, 0.3)",
                    color: "#D4956A",
                  }}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Ignition Plan
                </span>
              </div>
              <h2 className="text-xl font-serif text-text-primary text-center">
                Let&apos;s get you set up
              </h2>
              <p className="text-text-secondary text-sm text-center mt-1">
                Just 3 things and Maya will take it from here
              </p>
            </div>

            {/* Card Body */}
            <div className="p-6 space-y-6">
              {/* Step 1: Website URL */}
              <div
                className={`transition-all duration-300 ${
                  currentStep !== "website" && websiteValid ? "opacity-60" : ""
                }`}
              >
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Your Agency Website
                </label>
                <div className="relative">
                  <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleWebsiteSubmit()}
                    placeholder="https://youragency.com.au"
                    disabled={currentStep !== "website"}
                    className="w-full pl-12 pr-4 py-3.5 rounded-xl
                      text-text-primary placeholder-text-muted text-[15px]
                      transition-all duration-200
                      disabled:opacity-60 disabled:cursor-not-allowed"
                    style={{
                      backgroundColor: "rgba(255, 255, 255, 0.03)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                    }}
                    onFocus={(e) =>
                      (e.target.style.borderColor = "#D4956A")
                    }
                    onBlur={(e) =>
                      (e.target.style.borderColor =
                        "rgba(255, 255, 255, 0.08)")
                    }
                    autoFocus
                  />
                  {websiteValid && currentStep === "website" && (
                    <button
                      onClick={handleWebsiteSubmit}
                      className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg
                        text-xs font-medium gradient-premium text-text-primary"
                    >
                      Continue
                    </button>
                  )}
                  {websiteValid && currentStep !== "website" && (
                    <Check className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-status-success" />
                  )}
                </div>
              </div>

              {/* Auto-provision Notice */}
              <div
                className={`rounded-xl p-4 transition-all duration-300 ${
                  currentStep === "website" && !websiteValid ? "opacity-50" : ""
                }`}
                style={{
                  backgroundColor: "rgba(16, 185, 129, 0.08)",
                  border: "1px solid rgba(16, 185, 129, 0.2)",
                }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ backgroundColor: "rgba(16, 185, 129, 0.2)" }}
                  >
                    <Check className="w-3 h-3 text-status-success" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-status-success">
                      Email &amp; Phone auto-provisioned
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">
                      From pre-warmed pool for immediate deliverability
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 2: Integrations */}
              <div
                style={{
                  opacity: currentStep === "website" ? 0 : 1,
                  transform:
                    currentStep === "website"
                      ? "translateY(10px)"
                      : "translateY(0)",
                  transition: "all 0.4s ease",
                  pointerEvents: currentStep === "website" ? "none" : "auto",
                }}
              >
                <div className="relative my-2">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-border-subtle" />
                  </div>
                  <div className="relative flex justify-center">
                    <span
                      className="px-4 text-xs text-text-muted uppercase tracking-wider"
                      style={{ backgroundColor: "#0C0A08" }}
                    >
                      Connect Your Tools
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-6">
                  {/* HubSpot CRM */}
                  <div className="space-y-2">
                    <button
                      onClick={handleHubspotConnect}
                      disabled={hubspotConnected || isHubspotLoading}
                      className={`
                        relative flex flex-col items-center justify-center p-5 rounded-xl w-full
                        transition-all duration-200 glass-surface-hover
                        ${hubspotConnected ? "border-status-success/30" : "hover:border-accent-primary/50"}
                        disabled:cursor-not-allowed
                      `}
                      style={{
                        backgroundColor: hubspotConnected
                          ? "rgba(16, 185, 129, 0.05)"
                          : "rgba(255, 255, 255, 0.03)",
                        border: `1px solid ${
                          hubspotConnected
                            ? "rgba(16, 185, 129, 0.3)"
                            : "rgba(255, 255, 255, 0.08)"
                        }`,
                      }}
                    >
                      <div
                        className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider"
                        style={{
                          backgroundColor: hubspotConnected
                            ? "rgba(16, 185, 129, 0.2)"
                            : "rgba(212, 149, 106, 0.2)",
                          color: hubspotConnected ? "#10B981" : "#D4956A",
                        }}
                      >
                        Required
                      </div>
                      {hubspotConnected && (
                        <div className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                          <Check className="w-3 h-3 text-text-primary" />
                        </div>
                      )}
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                        style={{ backgroundColor: "rgba(255, 122, 89, 0.15)" }}
                      >
                        {isHubspotLoading ? (
                          <div className="w-5 h-5 border-2 border-[#FF7A59] border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <span className="text-[#FF7A59] font-bold text-sm">
                            H
                          </span>
                        )}
                      </div>
                      <span className="text-sm font-medium text-text-primary">
                        HubSpot CRM
                      </span>
                      <span className="text-[11px] text-text-muted mt-1">
                        {hubspotConnected
                          ? "Connected ✓"
                          : isHubspotLoading
                          ? "Connecting..."
                          : "Click to connect"}
                      </span>
                    </button>
                    {!hubspotConnected && (
                      <p className="text-[10px] text-text-muted text-center px-2">
                        Protects your existing clients from outreach and tracks
                        booked meetings
                      </p>
                    )}
                  </div>

                  {/* LinkedIn */}
                  <div className="space-y-2">
                    <button
                      onClick={handleLinkedinConnect}
                      disabled={linkedinConnected || isLinkedinLoading}
                      className={`
                        relative flex flex-col items-center justify-center p-5 rounded-xl w-full
                        transition-all duration-200 glass-surface-hover
                        ${linkedinConnected ? "border-status-success/30" : "hover:border-accent-primary/50"}
                        disabled:cursor-not-allowed
                      `}
                      style={{
                        backgroundColor: linkedinConnected
                          ? "rgba(16, 185, 129, 0.05)"
                          : "rgba(255, 255, 255, 0.03)",
                        border: `1px solid ${
                          linkedinConnected
                            ? "rgba(16, 185, 129, 0.3)"
                            : "rgba(255, 255, 255, 0.08)"
                        }`,
                      }}
                    >
                      <div
                        className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider"
                        style={{
                          backgroundColor: linkedinConnected
                            ? "rgba(16, 185, 129, 0.2)"
                            : "rgba(212, 149, 106, 0.2)",
                          color: linkedinConnected ? "#10B981" : "#D4956A",
                        }}
                      >
                        Required
                      </div>
                      {linkedinConnected && (
                        <div className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                          <Check className="w-3 h-3 text-text-primary" />
                        </div>
                      )}
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                        style={{
                          backgroundColor: "rgba(10, 102, 194, 0.15)",
                        }}
                      >
                        {isLinkedinLoading ? (
                          <div className="w-5 h-5 border-2 border-[#0A66C2] border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <Linkedin className="w-5 h-5 text-[#0A66C2]" />
                        )}
                      </div>
                      <span className="text-sm font-medium text-text-primary">
                        LinkedIn
                      </span>
                      <span className="text-[11px] text-text-muted mt-1">
                        {linkedinConnected
                          ? "Connected ✓"
                          : isLinkedinLoading
                          ? "Connecting..."
                          : "Click to connect"}
                      </span>
                    </button>
                    {!linkedinConnected && (
                      <p className="text-[10px] text-text-muted text-center px-2">
                        Enables LinkedIn outreach and protects your network from
                        outreach
                      </p>
                    )}
                  </div>
                </div>

                {/* Gate Warning */}
                {currentStep === "integrations" &&
                  (!hubspotConnected || !linkedinConnected) && (
                    <div
                      className="mt-4 rounded-xl p-4 flex items-start gap-3"
                      style={{
                        backgroundColor: "rgba(212, 149, 106, 0.1)",
                        border: "1px solid rgba(212, 149, 106, 0.3)",
                      }}
                    >
                      <AlertCircle className="w-5 h-5 text-accent-primary flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-accent-primary">
                          Both connections required to continue
                        </p>
                        <p className="text-xs text-text-muted mt-1">
                          Connect{" "}
                          {!hubspotConnected && !linkedinConnected
                            ? "both HubSpot CRM and LinkedIn"
                            : !hubspotConnected
                            ? "HubSpot CRM"
                            : "LinkedIn"}{" "}
                          to launch your dashboard
                        </p>
                      </div>
                    </div>
                  )}
              </div>

              {/* Launch Button */}
              <button
                onClick={handleLaunch}
                disabled={!canLaunch || isLoading}
                className="w-full py-4 rounded-xl text-[15px] font-semibold
                  transition-all duration-200 flex items-center justify-center gap-2
                  disabled:opacity-50 disabled:cursor-not-allowed
                  hover:shadow-glow-md"
                style={{
                  background: canLaunch
                    ? "linear-gradient(135deg, #D4956A 0%, #E0A87D 100%)"
                    : "rgba(255, 255, 255, 0.06)",
                  color: canLaunch ? "#0C0A08" : "#6B6560",
                }}
              >
                {isLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    <span>Analyzing your agency...</span>
                  </>
                ) : error ? (
                  <>
                    <RefreshCw className="w-5 h-5" />
                    Retry Launch
                  </>
                ) : (
                  <>
                    Launch Dashboard
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </div>

            <div className="px-6 py-4 border-t border-border-subtle">
              <p className="text-xs text-text-muted text-center">
                Need help?{" "}
                <a
                  href="mailto:support@agency-os.com"
                  className="text-accent-primary hover:underline"
                >
                  Contact support
                </a>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Maya Overlay */}
      <MayaOverlay
        currentStep={currentStep}
        stepProgress={mayaProgress}
        isTyping={isLoading || isHubspotLoading || isLinkedinLoading || jobIsRunning}
        isPulsing={true}
        isMinimised={isMayaMinimised}
        onMinimise={() => setIsMayaMinimised(true)}
        onMaximise={() => setIsMayaMinimised(false)}
        position="bottom-right"
      />
    </div>
  );
}

// ─── ICP Field Component ───────────────────────────────────────────────────

interface ICPFieldProps {
  icon: React.ReactNode;
  label: string;
  values: string[];
  editMode: boolean;
  onEdit: (values: string[]) => void;
}

function ICPField({ icon, label, values, editMode, onEdit }: ICPFieldProps) {
  const [inputVal, setInputVal] = useState(values.join(", "));

  // Sync when values change externally
  useEffect(() => {
    setInputVal(values.join(", "));
  }, [values]);

  const handleChange = (val: string) => {
    setInputVal(val);
    onEdit(
      val
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    );
  };

  return (
    <div
      className="rounded-xl p-4"
      style={{
        backgroundColor: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-text-muted">{icon}</span>
        <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          {label}
        </span>
      </div>
      {editMode ? (
        <input
          type="text"
          value={inputVal}
          onChange={(e) => handleChange(e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm text-text-primary bg-transparent"
          style={{
            backgroundColor: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(212, 149, 106, 0.4)",
          }}
          placeholder="Comma-separated values..."
        />
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {values.length > 0 ? (
            values.slice(0, 6).map((v, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded-full text-xs font-medium"
                style={{
                  backgroundColor: "rgba(212, 149, 106, 0.12)",
                  color: "#D4956A",
                  border: "1px solid rgba(212, 149, 106, 0.25)",
                }}
              >
                {v}
              </span>
            ))
          ) : (
            <span className="text-xs text-text-muted italic">
              Not detected
            </span>
          )}
          {values.length > 6 && (
            <span className="text-xs text-text-muted">
              +{values.length - 6} more
            </span>
          )}
        </div>
      )}
    </div>
  );
}
