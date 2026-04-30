"use client";

/**
 * FILE: frontend/app/onboarding/agency/page.tsx
 * PURPOSE: Agency profile step — website scrape + service confirmation
 * DIRECTIVE: #309 — Onboarding rebuild
 * DESIGN: Cream #F7F3EE, Ink #0C0A08, Amber #D4956A
 * APIS:
 *   POST /api/v1/onboarding/analyze        { website_url } → { job_id }
 *   GET  /api/v1/onboarding/status/{id}    → { status, progress_percent, ... }
 *   GET  /api/v1/onboarding/result/{id}    → ICPProfile
 *   POST /api/v1/onboarding/confirm        → save confirmed data
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  Check,
  Globe,
  Loader2,
  RefreshCw,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const POLL_MS = 3000;

type JobStatus = "pending" | "running" | "completed" | "failed";

interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  current_step: string | null;
  progress_percent: number;
  error_message: string | null;
}

interface AgencyProfile {
  company_name: string;
  website_url: string;
  services_offered: string[];
  value_proposition: string;
  case_studies?: string[];
}

type PageState = "url_entry" | "analyzing" | "review" | "confirming";

export default function AgencyOnboardingPage() {
  const router = useRouter();
  const [pageState, setPageState] = useState<PageState>("url_entry");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [urlValid, setUrlValid] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [profile, setProfile] = useState<AgencyProfile | null>(null);
  const [checkedServices, setCheckedServices] = useState<Set<string>>(new Set());
  const [additionalNotes, setAdditionalNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const profileFetchedRef = useRef(false);

  // URL validation
  useEffect(() => {
    try {
      if (websiteUrl) {
        new URL(websiteUrl.startsWith("http") ? websiteUrl : `https://${websiteUrl}`);
        setUrlValid(true);
      } else {
        setUrlValid(false);
      }
    } catch {
      setUrlValid(false);
    }
  }, [websiteUrl]);

  const fetchStatus = useCallback(async (id: string) => {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/status/${id}`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Status fetch failed (${res.status})`);
    return res.json() as Promise<JobStatusResponse>;
  }, []);

  const fetchResult = useCallback(async (id: string) => {
    const res = await fetch(`${API_BASE}/api/v1/onboarding/result/${id}`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Result fetch failed (${res.status})`);
    return res.json() as Promise<AgencyProfile>;
  }, []);

  // Polling
  useEffect(() => {
    if (pageState !== "analyzing" || !jobId) return;
    profileFetchedRef.current = false;

    const poll = async () => {
      try {
        const status = await fetchStatus(jobId);
        setJobStatus(status);
        if (status.status === "completed" && !profileFetchedRef.current) {
          profileFetchedRef.current = true;
          clearInterval(pollRef.current!);
          pollRef.current = null;
          const data = await fetchResult(jobId);
          setProfile(data);
          setCheckedServices(new Set(data.services_offered));
          setPageState("review");
        } else if (status.status === "failed") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setError(status.error_message ?? "Analysis failed");
          setPageState("url_entry");
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    };

    poll();
    pollRef.current = setInterval(poll, POLL_MS);
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [pageState, jobId, fetchStatus, fetchResult]);

  const handleAnalyze = async () => {
    setError(null);
    const normalizedUrl = websiteUrl.startsWith("http")
      ? websiteUrl
      : `https://${websiteUrl}`;
    try {
      const res = await fetch(`${API_BASE}/api/v1/onboarding/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ website_url: normalizedUrl }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Analysis start failed (${res.status})`);
      }
      const data = await res.json();
      setJobId(data.job_id);
      setPageState("analyzing");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
    }
  };

  const toggleService = (service: string) => {
    setCheckedServices((prev) => {
      const next = new Set(prev);
      if (next.has(service)) {
        next.delete(service);
      } else {
        next.add(service);
      }
      return next;
    });
  };

  const handleConfirm = async () => {
    if (!profile) return;
    setPageState("confirming");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/onboarding/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          job_id: jobId,
          confirmed_services: Array.from(checkedServices),
          additional_notes: additionalNotes || null,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Confirm failed (${res.status})`);
      }
      router.push("/onboarding/service-area");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
      setPageState("review");
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-16 bg-cream text-ink"
    >
      <div className="w-full max-w-xl">
        {/* Step label */}
        <p
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "11px",
            letterSpacing: "0.12em",
            color: "#D4956A",
            textTransform: "uppercase",
            marginBottom: "24px",
          }}
        >
          Step 3 of 4 — Your Agency
        </p>

        {/* Headline */}
        <h1
          style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 700,
            fontSize: "clamp(28px, 5vw, 40px)",
            lineHeight: 1.15,
            color: "#0C0A08",
            marginBottom: "12px",
          }}
        >
          Let&apos;s make sure we understand
          <br />
          <em>what you do</em>
        </h1>

        <p
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 300,
            fontSize: "16px",
            lineHeight: 1.6,
            color: "#4A4540",
            marginBottom: "36px",
          }}
        >
          Enter your website and we&apos;ll extract your services and positioning
          automatically. You can correct anything we get wrong.
        </p>

        {/* Error */}
        {error && (
          <div
            style={{
              border: "1px solid rgba(220,50,50,0.3)",
              background: "rgba(220,50,50,0.05)",
              padding: "12px 16px",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <AlertCircle size={15} style={{ color: "#DC3232", flexShrink: 0 }} />
            <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "13px", color: "#DC3232" }}>
              {error}
            </p>
          </div>
        )}

        {/* URL Entry */}
        {(pageState === "url_entry" || pageState === "analyzing") && (
          <div>
            <div style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <Globe
                  size={15}
                  style={{
                    position: "absolute",
                    left: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "#9A8F85",
                  }}
                />
                <input
                  type="text"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && urlValid && pageState === "url_entry" && handleAnalyze()}
                  placeholder="https://youragency.com.au"
                  disabled={pageState === "analyzing"}
                  style={{
                    width: "100%",
                    background: "rgba(255,255,255,0.6)",
                    border: "1px solid rgba(12,10,8,0.15)",
                    padding: "12px 12px 12px 36px",
                    fontFamily: "'DM Sans', sans-serif",
                    fontSize: "14px",
                    color: "#0C0A08",
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <button
                onClick={handleAnalyze}
                disabled={!urlValid || pageState === "analyzing"}
                style={{
                  background:
                    !urlValid || pageState === "analyzing"
                      ? "rgba(212,149,106,0.4)"
                      : "linear-gradient(135deg, #D4956A 0%, #C07D4E 100%)",
                  color: "#F7F3EE",
                  border: "none",
                  padding: "12px 20px",
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 500,
                  fontSize: "14px",
                  cursor: !urlValid || pageState === "analyzing" ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  whiteSpace: "nowrap",
                }}
              >
                {pageState === "analyzing" ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze my site"
                )}
              </button>
            </div>

            {pageState === "analyzing" && jobStatus && (
              <div
                style={{
                  border: "1px solid rgba(212,149,106,0.2)",
                  background: "rgba(212,149,106,0.04)",
                  padding: "16px",
                  marginTop: "16px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#D4956A" }}>
                    {jobStatus.current_step ?? "Processing..."}
                  </p>
                  <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#D4956A" }}>
                    {jobStatus.progress_percent}%
                  </p>
                </div>
                <div style={{ background: "rgba(212,149,106,0.15)", height: "3px" }}>
                  <div
                    style={{
                      background: "#D4956A",
                      height: "100%",
                      width: `${jobStatus.progress_percent}%`,
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Review panel */}
        {(pageState === "review" || pageState === "confirming") && profile && (
          <div>
            {/* Services */}
            <div
              style={{
                border: "1px solid rgba(12,10,8,0.1)",
                background: "rgba(255,255,255,0.5)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                padding: "20px",
                marginBottom: "16px",
              }}
            >
              <p
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "11px",
                  letterSpacing: "0.1em",
                  color: "#D4956A",
                  textTransform: "uppercase",
                  marginBottom: "14px",
                }}
              >
                Services we identified
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {profile.services_offered.map((service) => (
                  <label
                    key={service}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      cursor: "pointer",
                      fontFamily: "'DM Sans', sans-serif",
                      fontSize: "14px",
                      color: "#0C0A08",
                    }}
                  >
                    <div
                      onClick={() => toggleService(service)}
                      style={{
                        width: "18px",
                        height: "18px",
                        border: checkedServices.has(service)
                          ? "1px solid #D4956A"
                          : "1px solid rgba(12,10,8,0.25)",
                        background: checkedServices.has(service)
                          ? "#D4956A"
                          : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        cursor: "pointer",
                      }}
                    >
                      {checkedServices.has(service) && (
                        <Check size={11} style={{ color: "#F7F3EE" }} />
                      )}
                    </div>
                    {service}
                  </label>
                ))}
              </div>
            </div>

            {/* Positioning */}
            {profile.value_proposition && (
              <div
                style={{
                  border: "1px solid rgba(12,10,8,0.1)",
                  background: "rgba(255,255,255,0.5)",
                  backdropFilter: "blur(20px)",
                  WebkitBackdropFilter: "blur(20px)",
                  padding: "20px",
                  marginBottom: "16px",
                }}
              >
                <p
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: "11px",
                    letterSpacing: "0.1em",
                    color: "#D4956A",
                    textTransform: "uppercase",
                    marginBottom: "10px",
                  }}
                >
                  Positioning
                </p>
                <p
                  style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontWeight: 300,
                    fontSize: "14px",
                    lineHeight: 1.65,
                    color: "#3A3530",
                  }}
                >
                  {profile.value_proposition}
                </p>
              </div>
            )}

            {/* Case studies */}
            {profile.case_studies && profile.case_studies.length > 0 && (
              <div
                style={{
                  border: "1px solid rgba(12,10,8,0.1)",
                  background: "rgba(255,255,255,0.5)",
                  backdropFilter: "blur(20px)",
                  WebkitBackdropFilter: "blur(20px)",
                  padding: "20px",
                  marginBottom: "16px",
                }}
              >
                <p
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: "11px",
                    letterSpacing: "0.1em",
                    color: "#D4956A",
                    textTransform: "uppercase",
                    marginBottom: "10px",
                  }}
                >
                  Case studies found
                </p>
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {profile.case_studies.map((cs, i) => (
                    <li
                      key={i}
                      style={{
                        fontFamily: "'DM Sans', sans-serif",
                        fontSize: "13px",
                        color: "#4A4540",
                        paddingBottom: "6px",
                        borderBottom: i < profile.case_studies!.length - 1 ? "1px solid rgba(12,10,8,0.06)" : "none",
                        marginBottom: "6px",
                      }}
                    >
                      {cs}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Free text correction field */}
            <div style={{ marginBottom: "24px" }}>
              <label
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "11px",
                  letterSpacing: "0.1em",
                  color: "#9A8F85",
                  textTransform: "uppercase",
                  display: "block",
                  marginBottom: "8px",
                }}
              >
                Anything we missed or got wrong?
              </label>
              <textarea
                value={additionalNotes}
                onChange={(e) => setAdditionalNotes(e.target.value)}
                rows={3}
                placeholder="Optional — add context, correct mistakes, or describe services not on your site."
                style={{
                  width: "100%",
                  background: "rgba(255,255,255,0.6)",
                  border: "1px solid rgba(12,10,8,0.15)",
                  padding: "12px",
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: "13px",
                  color: "#0C0A08",
                  outline: "none",
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
              />
            </div>

            {/* Retry + Confirm row */}
            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <button
                onClick={() => {
                  setProfile(null);
                  setJobId(null);
                  setJobStatus(null);
                  setError(null);
                  setPageState("url_entry");
                }}
                style={{
                  background: "none",
                  border: "1px solid rgba(12,10,8,0.15)",
                  padding: "12px 16px",
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: "13px",
                  color: "#6A5F55",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <RefreshCw size={13} />
                Re-analyze
              </button>

              <button
                onClick={handleConfirm}
                disabled={pageState === "confirming" || checkedServices.size === 0}
                style={{
                  flex: 1,
                  background:
                    pageState === "confirming" || checkedServices.size === 0
                      ? "rgba(212,149,106,0.4)"
                      : "linear-gradient(135deg, #D4956A 0%, #C07D4E 100%)",
                  color: "#F7F3EE",
                  border: "none",
                  padding: "13px 20px",
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 500,
                  fontSize: "14px",
                  cursor: pageState === "confirming" || checkedServices.size === 0 ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                }}
              >
                {pageState === "confirming" ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    Yes, this is my agency
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
