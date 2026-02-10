"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Star } from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [hubspotConnected, setHubspotConnected] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);

  const handleLaunch = () => {
    if (!websiteUrl) {
      alert("Please enter your website URL");
      return;
    }
    router.push("/dashboard?onboarding=true");
  };

  return (
    <div className="min-h-screen bg-bg-base flex items-center justify-center p-5">
      <div className="w-full max-w-[480px]">
        {/* Logo Section */}
        <div className="text-center mb-10">
          <div className="w-12 h-12 mx-auto mb-4">
            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="48" height="48" rx="12" fill="url(#logo-gradient)" />
              <path
                d="M14 24L20 30L34 16"
                stroke="white"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient id="logo-gradient" x1="0" y1="0" x2="48" y2="48">
                  <stop stopColor="#7C3AED" />
                  <stop offset="1" stopColor="#9D5CFF" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">Agency OS</h1>
          <p className="text-sm text-text-secondary">
            Your digital employee is ready to work
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-bg-surface border border-border-subtle rounded-2xl p-8">
          {/* Card Header */}
          <div className="text-center mb-8">
            {/* Tier Badge */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-accent-primary/15 to-[#9D5CFF]/15 border border-accent-primary/30 rounded-full text-xs font-semibold text-accent-primary-hover mb-6">
              <Star className="w-3.5 h-3.5" />
              Ignition Plan
            </div>
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              Let&apos;s get you set up
            </h2>
            <p className="text-sm text-text-secondary">
              Just 3 things and Maya will take it from here
            </p>
          </div>

          {/* Website URL Input */}
          <div className="mb-6">
            <label className="block text-[13px] font-medium text-text-secondary mb-2">
              Your Agency Website
            </label>
            <input
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://youragency.com.au"
              autoFocus
              className="w-full px-4 py-3.5 bg-bg-elevated border border-border-subtle rounded-[10px]
                text-[15px] text-text-primary placeholder-text-muted
                focus:outline-none focus:border-accent-primary focus:ring-[3px] focus:ring-accent-primary/15
                transition-all duration-200"
            />
          </div>

          {/* Auto-provision Notice */}
          <div className="flex items-center gap-2 px-4 py-3 bg-status-success/[0.08] border border-status-success/20 rounded-[10px] mb-6">
            <svg
              className="w-[18px] h-[18px] text-status-success flex-shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span className="text-[13px] text-text-secondary">
              <strong className="text-status-success">Email &amp; Phone</strong> auto-provisioned
              from pre-warmed pool
            </span>
          </div>

          {/* Divider */}
          <div className="flex items-center my-7">
            <div className="flex-1 h-px bg-border-subtle" />
            <span className="px-4 text-xs text-text-muted uppercase tracking-wide">
              Connect Your Tools
            </span>
            <div className="flex-1 h-px bg-border-subtle" />
          </div>

          {/* Integration Buttons Grid */}
          <div className="grid grid-cols-2 gap-3 mb-7">
            {/* HubSpot CRM */}
            <button
              onClick={() => setHubspotConnected(!hubspotConnected)}
              className={`flex flex-col items-center gap-2.5 p-5 rounded-xl border transition-all duration-200 ${
                hubspotConnected
                  ? "bg-status-success/[0.05] border-status-success"
                  : "bg-bg-elevated border-border-subtle hover:border-accent-primary hover:bg-accent-primary/[0.05]"
              }`}
            >
              <svg viewBox="0 0 32 32" fill="none" className="w-8 h-8">
                <rect width="32" height="32" rx="6" fill="#FF7A59" />
                <path
                  d="M16 8v16M8 16h16"
                  stroke="white"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
              <span className="text-[13px] font-medium text-text-primary">HubSpot CRM</span>
              <span
                className={`text-[11px] ${
                  hubspotConnected ? "text-status-success" : "text-text-muted"
                }`}
              >
                {hubspotConnected ? "Connected ✓" : "Click to connect"}
              </span>
            </button>

            {/* LinkedIn */}
            <button
              onClick={() => setLinkedinConnected(!linkedinConnected)}
              className={`flex flex-col items-center gap-2.5 p-5 rounded-xl border transition-all duration-200 ${
                linkedinConnected
                  ? "bg-status-success/[0.05] border-status-success"
                  : "bg-bg-elevated border-border-subtle hover:border-accent-primary hover:bg-accent-primary/[0.05]"
              }`}
            >
              <svg viewBox="0 0 32 32" fill="none" className="w-8 h-8">
                <rect width="32" height="32" rx="6" fill="#0A66C2" />
                <path
                  d="M10 13v9M10 10v.01M14 22v-5c0-2 1-3 3-3s3 1 3 3v5M14 13v9"
                  stroke="white"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-[13px] font-medium text-text-primary">LinkedIn</span>
              <span
                className={`text-[11px] ${
                  linkedinConnected ? "text-status-success" : "text-text-muted"
                }`}
              >
                {linkedinConnected ? "Connected ✓" : "Click to connect"}
              </span>
            </button>
          </div>

          {/* Launch Button */}
          <button
            onClick={handleLaunch}
            className="w-full py-4 px-6 bg-gradient-to-br from-accent-primary to-[#9D5CFF] 
              text-white text-[15px] font-semibold rounded-xl
              hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(124,58,237,0.35)]
              transition-all duration-200"
          >
            Launch Dashboard →
          </button>

          {/* Help Link */}
          <p className="text-center mt-5 text-xs text-text-muted">
            Need help?{" "}
            <a href="#" className="text-accent-primary hover:underline">
              Contact support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
