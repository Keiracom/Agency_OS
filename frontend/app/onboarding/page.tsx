"use client";

/**
 * FILE: frontend/app/onboarding/page.tsx
 * PURPOSE: Agency onboarding flow - website URL + integrations
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
 * - Gate Check: GET /api/v1/onboarding/gates
 */

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Globe, Linkedin, ArrowRight, Sparkles, AlertCircle, RefreshCw } from "lucide-react";
import { MayaOverlay } from "@/components/maya";

type OnboardingStep = 'website' | 'integrations' | 'complete';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function OnboardingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [websiteValid, setWebsiteValid] = useState(false);
  const [hubspotConnected, setHubspotConnected] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('website');
  const [isLoading, setIsLoading] = useState(false);
  const [isHubspotLoading, setIsHubspotLoading] = useState(false);
  const [isLinkedinLoading, setIsLinkedinLoading] = useState(false);
  const [isMayaMinimised, setIsMayaMinimised] = useState(false);
  const [mayaProgress, setMayaProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Handle OAuth callbacks from query params
  useEffect(() => {
    const hubspotSuccess = searchParams.get('hubspot') === 'connected';
    const linkedinSuccess = searchParams.get('linkedin') === 'connected';
    const oauthError = searchParams.get('oauth_error');

    if (hubspotSuccess) {
      setHubspotConnected(true);
      setCurrentStep('integrations');
    }
    if (linkedinSuccess) {
      setLinkedinConnected(true);
      setCurrentStep('integrations');
    }
    if (oauthError) {
      setError(`OAuth failed: ${oauthError}`);
    }
  }, [searchParams]);

  // Validate website URL
  useEffect(() => {
    try {
      if (websiteUrl) {
        new URL(websiteUrl.startsWith('http') ? websiteUrl : `https://${websiteUrl}`);
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
      'website': 33,
      'integrations': 66,
      'complete': 100,
    };
    setMayaProgress(progressMap[currentStep] || 0);
  }, [currentStep]);

  // Progressive disclosure - advance to integrations when URL is valid
  const handleWebsiteSubmit = () => {
    if (websiteValid) {
      setCurrentStep('integrations');
    }
  };

  // HubSpot OAuth - calls GET /api/v1/crm/auth/hubspot
  const handleHubspotConnect = useCallback(async () => {
    setError(null);
    setIsHubspotLoading(true);
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/crm/auth/hubspot`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HubSpot auth failed (${response.status})`);
      }

      const data = await response.json();
      
      if (data.redirect_url || data.auth_url || data.url) {
        // Open OAuth in new window or redirect
        const authUrl = data.redirect_url || data.auth_url || data.url;
        window.location.href = authUrl;
      } else {
        // Direct connection successful (no OAuth redirect needed)
        setHubspotConnected(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect HubSpot';
      setError(message);
      console.error('HubSpot connect error:', err);
    } finally {
      setIsHubspotLoading(false);
    }
  }, []);

  // LinkedIn OAuth - calls GET /api/v1/linkedin/connect
  const handleLinkedinConnect = useCallback(async () => {
    setError(null);
    setIsLinkedinLoading(true);
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/linkedin/connect`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `LinkedIn auth failed (${response.status})`);
      }

      const data = await response.json();
      
      if (data.redirect_url || data.auth_url || data.url || data.hosted_auth_url) {
        // Unipile returns hosted_auth_url for LinkedIn OAuth
        const authUrl = data.hosted_auth_url || data.redirect_url || data.auth_url || data.url;
        window.location.href = authUrl;
      } else {
        // Direct connection successful
        setLinkedinConnected(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect LinkedIn';
      setError(message);
      console.error('LinkedIn connect error:', err);
    } finally {
      setIsLinkedinLoading(false);
    }
  }, []);

  // Launch - calls POST /api/v1/onboarding/analyze for ICP extraction
  const handleLaunch = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    setCurrentStep('complete');
    
    try {
      // Normalize website URL
      const normalizedUrl = websiteUrl.startsWith('http') 
        ? websiteUrl 
        : `https://${websiteUrl}`;

      const response = await fetch(`${API_BASE}/api/v1/onboarding/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          website_url: normalizedUrl,
          crm_connected: hubspotConnected,
          linkedin_connected: linkedinConnected,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Analysis failed (${response.status})`);
      }

      const data = await response.json();

      // The response contains agency_service_profile and agency_communication_profile
      // These are written to the backend's database by the analyze endpoint
      // We can optionally store a reference in localStorage for the dashboard
      if (data.agency_service_profile || data.agency_communication_profile) {
        try {
          localStorage.setItem('onboarding_profile', JSON.stringify({
            service_profile: data.agency_service_profile,
            communication_profile: data.agency_communication_profile,
            completed_at: new Date().toISOString(),
          }));
        } catch {
          // localStorage not available, continue anyway
        }
      }

      // Success - redirect to dashboard
      router.push("/dashboard?onboarding=true");
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to analyze website';
      setError(message);
      setCurrentStep('integrations'); // Go back to allow retry
      console.error('Launch/analyze error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [websiteUrl, hubspotConnected, linkedinConnected, router]);

  // MANDATORY GATES: Both LinkedIn AND CRM must be connected to proceed
  // Architecture Decision: No bypass permitted
  const canLaunch = websiteValid && hubspotConnected && linkedinConnected;

  // Dismiss error
  const dismissError = () => setError(null);

  return (
    <div 
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{ backgroundColor: '#0C0A08' }}
    >
      <div className="w-full max-w-[480px]">
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
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
            }}
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-400">{error}</p>
              <button 
                onClick={dismissError}
                className="text-xs text-red-300 hover:text-red-200 mt-1 underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Main Card - Glassmorphism */}
        <div className="glass-surface rounded-2xl overflow-hidden">
          {/* Card Header */}
          <div className="p-6 border-b border-border-subtle">
            <div className="flex items-center justify-center mb-4">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold"
                style={{ 
                  background: 'linear-gradient(135deg, rgba(212, 149, 106, 0.15), rgba(224, 168, 125, 0.15))',
                  border: '1px solid rgba(212, 149, 106, 0.3)',
                  color: '#D4956A'
                }}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Ignition Plan
              </span>
            </div>
            <h2 className="text-xl font-serif text-text-primary text-center">
              Let's get you set up
            </h2>
            <p className="text-text-secondary text-sm text-center mt-1">
              Just 3 things and Maya will take it from here
            </p>
          </div>

          {/* Card Body */}
          <div className="p-6 space-y-6">
            {/* Step 1: Website URL Input */}
            <div className={`transition-all duration-300 ${currentStep !== 'website' && websiteValid ? 'opacity-60' : ''}`}>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Your Agency Website
              </label>
              <div className="relative">
                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="url"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleWebsiteSubmit()}
                  placeholder="https://youragency.com.au"
                  disabled={currentStep !== 'website'}
                  className="w-full pl-12 pr-4 py-3.5 rounded-xl
                    text-text-primary placeholder-text-muted text-[15px]
                    transition-all duration-200
                    disabled:opacity-60 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#D4956A'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)'}
                  autoFocus
                />
                {websiteValid && currentStep === 'website' && (
                  <button
                    onClick={handleWebsiteSubmit}
                    className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg
                      text-xs font-medium gradient-premium text-text-primary"
                  >
                    Continue
                  </button>
                )}
                {websiteValid && currentStep !== 'website' && (
                  <Check className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-status-success" />
                )}
              </div>
            </div>

            {/* Auto-provision Notice */}
            <div 
              className={`rounded-xl p-4 transition-all duration-300 ${
                currentStep === 'website' && !websiteValid ? 'opacity-50' : ''
              }`}
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
              }}
            >
              <div className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                  style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)' }}
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

            {/* Step 2: Integrations - Progressive disclosure */}
            <div className={`step-reveal ${currentStep === 'integrations' || currentStep === 'complete' ? 'active' : ''}`}
              style={{ 
                opacity: currentStep === 'website' ? 0 : 1,
                transform: currentStep === 'website' ? 'translateY(10px)' : 'translateY(0)',
                transition: 'all 0.4s ease',
                pointerEvents: currentStep === 'website' ? 'none' : 'auto'
              }}
            >
              {/* Divider */}
              <div className="relative my-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border-subtle" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-4 text-xs text-text-muted uppercase tracking-wider"
                    style={{ backgroundColor: '#0C0A08' }}
                  >
                    Connect Your Tools
                  </span>
                </div>
              </div>

              {/* Integration Buttons Grid */}
              <div className="grid grid-cols-2 gap-3 mt-6">
                {/* HubSpot CRM - REQUIRED */}
                <div className="space-y-2">
                  <button
                    onClick={handleHubspotConnect}
                    disabled={hubspotConnected || isHubspotLoading}
                    className={`
                      relative flex flex-col items-center justify-center p-5 rounded-xl w-full
                      transition-all duration-200 glass-surface-hover
                      ${hubspotConnected 
                        ? 'border-status-success/30' 
                        : 'hover:border-accent-primary/50'
                      }
                      disabled:cursor-not-allowed
                    `}
                    style={{
                      backgroundColor: hubspotConnected 
                        ? 'rgba(16, 185, 129, 0.05)' 
                        : 'rgba(255, 255, 255, 0.03)',
                      border: `1px solid ${hubspotConnected 
                        ? 'rgba(16, 185, 129, 0.3)' 
                        : 'rgba(255, 255, 255, 0.08)'
                      }`,
                    }}
                  >
                    {/* Required Badge */}
                    <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider"
                      style={{
                        backgroundColor: hubspotConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(212, 149, 106, 0.2)',
                        color: hubspotConnected ? '#10B981' : '#D4956A',
                      }}
                    >
                      Required
                    </div>
                    
                    {hubspotConnected ? (
                      <div className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                        <Check className="w-3 h-3 text-text-primary" />
                      </div>
                    ) : null}
                    
                    {/* HubSpot Icon */}
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                      style={{ backgroundColor: 'rgba(255, 122, 89, 0.15)' }}
                    >
                      {isHubspotLoading ? (
                        <div className="w-5 h-5 border-2 border-[#FF7A59] border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <span className="text-[#FF7A59] font-bold text-sm">H</span>
                      )}
                    </div>
                    <span className="text-sm font-medium text-text-primary">HubSpot CRM</span>
                    <span className="text-[11px] text-text-muted mt-1">
                      {hubspotConnected ? 'Connected ✓' : isHubspotLoading ? 'Connecting...' : 'Click to connect'}
                    </span>
                  </button>
                  {/* CRM Gate Message */}
                  {!hubspotConnected && (
                    <p className="text-[10px] text-text-muted text-center px-2">
                      Protects your existing clients from outreach and tracks booked meetings
                    </p>
                  )}
                </div>

                {/* LinkedIn - REQUIRED */}
                <div className="space-y-2">
                  <button
                    onClick={handleLinkedinConnect}
                    disabled={linkedinConnected || isLinkedinLoading}
                    className={`
                      relative flex flex-col items-center justify-center p-5 rounded-xl w-full
                      transition-all duration-200 glass-surface-hover
                      ${linkedinConnected 
                        ? 'border-status-success/30' 
                        : 'hover:border-accent-primary/50'
                      }
                      disabled:cursor-not-allowed
                    `}
                    style={{
                      backgroundColor: linkedinConnected 
                        ? 'rgba(16, 185, 129, 0.05)' 
                        : 'rgba(255, 255, 255, 0.03)',
                      border: `1px solid ${linkedinConnected 
                        ? 'rgba(16, 185, 129, 0.3)' 
                        : 'rgba(255, 255, 255, 0.08)'
                      }`,
                    }}
                  >
                    {/* Required Badge */}
                    <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider"
                      style={{
                        backgroundColor: linkedinConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(212, 149, 106, 0.2)',
                        color: linkedinConnected ? '#10B981' : '#D4956A',
                      }}
                    >
                      Required
                    </div>
                    
                    {linkedinConnected ? (
                      <div className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                        <Check className="w-3 h-3 text-text-primary" />
                      </div>
                    ) : null}
                    
                    {/* LinkedIn Icon */}
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                      style={{ backgroundColor: 'rgba(10, 102, 194, 0.15)' }}
                    >
                      {isLinkedinLoading ? (
                        <div className="w-5 h-5 border-2 border-[#0A66C2] border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Linkedin className="w-5 h-5 text-[#0A66C2]" />
                      )}
                    </div>
                    <span className="text-sm font-medium text-text-primary">LinkedIn</span>
                    <span className="text-[11px] text-text-muted mt-1">
                      {linkedinConnected ? 'Connected ✓' : isLinkedinLoading ? 'Connecting...' : 'Click to connect'}
                    </span>
                  </button>
                  {/* LinkedIn Gate Message */}
                  {!linkedinConnected && (
                    <p className="text-[10px] text-text-muted text-center px-2">
                      Enables LinkedIn outreach and protects your network from outreach
                    </p>
                  )}
                </div>
              </div>

              {/* Gate Warning Banner - Shows when integrations are missing */}
              {(currentStep === 'integrations' || currentStep === 'complete') && (!hubspotConnected || !linkedinConnected) && (
                <div 
                  className="mt-4 rounded-xl p-4 flex items-start gap-3"
                  style={{
                    backgroundColor: 'rgba(212, 149, 106, 0.1)',
                    border: '1px solid rgba(212, 149, 106, 0.3)',
                  }}
                >
                  <AlertCircle className="w-5 h-5 text-accent-primary flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-accent-primary">
                      Both connections required to continue
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      Connect {!hubspotConnected && !linkedinConnected ? 'both HubSpot CRM and LinkedIn' : !hubspotConnected ? 'HubSpot CRM' : 'LinkedIn'} to launch your dashboard
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
                  ? 'linear-gradient(135deg, #D4956A 0%, #E0A87D 100%)'
                  : 'rgba(255, 255, 255, 0.06)',
                color: canLaunch ? '#0C0A08' : '#6B6560',
              }}
            >
              {isLoading ? (
                <>
                  <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  <span>Analyzing your agency...</span>
                </>
              ) : error && currentStep === 'integrations' ? (
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

          {/* Card Footer */}
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

        {/* Skeleton loader preview - shows what will load */}
        {currentStep === 'complete' && (
          <div className="mt-6 glass-surface rounded-xl p-4">
            <p className="text-xs text-text-muted mb-3">
              {isLoading ? 'Extracting ICP from your website...' : 'Preparing your dashboard...'}
            </p>
            <div className="space-y-3">
              <div className="skeleton h-4 w-3/4" />
              <div className="skeleton h-4 w-1/2" />
              <div className="skeleton h-4 w-2/3" />
            </div>
          </div>
        )}
      </div>

      {/* Maya Overlay - Sprint 4 */}
      <MayaOverlay
        currentStep={currentStep}
        stepProgress={mayaProgress}
        isTyping={isLoading || isHubspotLoading || isLinkedinLoading}
        isPulsing={true}
        isMinimised={isMayaMinimised}
        onMinimise={() => setIsMayaMinimised(true)}
        onMaximise={() => setIsMayaMinimised(false)}
        position="bottom-right"
      />
    </div>
  );
}
