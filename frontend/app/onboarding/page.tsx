"use client";

/**
 * FILE: frontend/app/onboarding/page.tsx
 * PURPOSE: Agency onboarding flow - website URL + integrations
 * SPRINT: Dashboard Sprint 1 - Onboarding Port
 * SSOT: frontend/design/html-prototypes/onboarding-v3.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Check, Globe, Linkedin, ArrowRight, Sparkles } from "lucide-react";
// MayaChatBubble - Sprint 4 work, not yet implemented

type OnboardingStep = 'website' | 'integrations' | 'complete';

export default function OnboardingPage() {
  const router = useRouter();
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [websiteValid, setWebsiteValid] = useState(false);
  const [hubspotConnected, setHubspotConnected] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('website');
  const [isLoading, setIsLoading] = useState(false);

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

  // Progressive disclosure - advance to integrations when URL is valid
  const handleWebsiteSubmit = () => {
    if (websiteValid) {
      setCurrentStep('integrations');
    }
  };

  // Handle OAuth placeholder clicks
  const handleHubspotConnect = () => {
    // OAuth placeholder - would trigger HubSpot OAuth flow
    setIsLoading(true);
    setTimeout(() => {
      setHubspotConnected(true);
      setIsLoading(false);
    }, 1000);
  };

  const handleLinkedinConnect = () => {
    // OAuth placeholder - would trigger LinkedIn OAuth flow
    setIsLoading(true);
    setTimeout(() => {
      setLinkedinConnected(true);
      setIsLoading(false);
    }, 1000);
  };

  const handleLaunch = () => {
    setIsLoading(true);
    // In production: POST to /api/v1/onboarding/analyze
    setTimeout(() => {
      router.push("/dashboard?onboarding=true");
    }, 500);
  };

  const canLaunch = websiteValid;

  return (
    <div 
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{ backgroundColor: '#0C0A08' }}
    >
      <div className="w-full max-w-[480px]">
        {/* Logo Section */}
        <div className="text-center mb-10">
          <div className="w-14 h-14 mx-auto mb-5 rounded-2xl gradient-premium flex items-center justify-center shadow-glow-md">
            <Check className="w-7 h-7 text-white" strokeWidth={3} />
          </div>
          <h1 className="text-3xl font-serif text-text-primary mb-2">
            Agency OS
          </h1>
          <p className="text-text-secondary text-sm">
            Your digital employee is ready to work
          </p>
        </div>

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
                      text-xs font-medium gradient-premium text-white"
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
                {/* HubSpot CRM */}
                <button
                  onClick={handleHubspotConnect}
                  disabled={hubspotConnected || isLoading}
                  className={`
                    relative flex flex-col items-center justify-center p-5 rounded-xl
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
                  {hubspotConnected ? (
                    <div className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  ) : null}
                  
                  {/* HubSpot Icon */}
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                    style={{ backgroundColor: 'rgba(255, 122, 89, 0.15)' }}
                  >
                    {isLoading && !hubspotConnected ? (
                      <div className="w-5 h-5 border-2 border-[#FF7A59] border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <span className="text-[#FF7A59] font-bold text-sm">H</span>
                    )}
                  </div>
                  <span className="text-sm font-medium text-text-primary">HubSpot CRM</span>
                  <span className="text-[11px] text-text-muted mt-1">
                    {hubspotConnected ? 'Connected ✓' : 'Click to connect'}
                  </span>
                </button>

                {/* LinkedIn */}
                <button
                  onClick={handleLinkedinConnect}
                  disabled={linkedinConnected || isLoading}
                  className={`
                    relative flex flex-col items-center justify-center p-5 rounded-xl
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
                  {linkedinConnected ? (
                    <div className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  ) : null}
                  
                  {/* LinkedIn Icon */}
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                    style={{ backgroundColor: 'rgba(10, 102, 194, 0.15)' }}
                  >
                    {isLoading && !linkedinConnected ? (
                      <div className="w-5 h-5 border-2 border-[#0A66C2] border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Linkedin className="w-5 h-5 text-[#0A66C2]" />
                    )}
                  </div>
                  <span className="text-sm font-medium text-text-primary">LinkedIn</span>
                  <span className="text-[11px] text-text-muted mt-1">
                    {linkedinConnected ? 'Connected ✓' : 'Click to connect'}
                  </span>
                </button>
              </div>
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
                <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
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
            <p className="text-xs text-text-muted mb-3">Preparing your dashboard...</p>
            <div className="space-y-3">
              <div className="skeleton h-4 w-3/4" />
              <div className="skeleton h-4 w-1/2" />
              <div className="skeleton h-4 w-2/3" />
            </div>
          </div>
        )}
      </div>

      {/* Maya Chat Bubble - Sprint 4 work, not yet implemented */}
    </div>
  );
}
