"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Globe, Linkedin } from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [hubspotConnected, setHubspotConnected] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);

  const handleLaunch = () => {
    router.push("/dashboard?onboarding=true");
  };

  return (
    <div className="min-h-screen bg-bg-base flex items-center justify-center px-4">
      <div className="w-full max-w-[480px]">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-accent-primary to-accent-blue rounded-2xl flex items-center justify-center shadow-glow-md">
            <Check className="w-8 h-8 text-white" strokeWidth={3} />
          </div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">
            Agency OS
          </h1>
          <p className="text-text-secondary">
            Your digital employee is ready to work
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-bg-surface border border-border-subtle rounded-2xl overflow-hidden">
          {/* Card Header */}
          <div className="p-6 border-b border-border-subtle">
            <div className="flex items-center gap-3 mb-4">
              <span className="px-3 py-1 bg-accent-primary/15 border border-accent-primary/30 rounded-full text-xs font-semibold text-accent-primary">
                Ignition Plan
              </span>
            </div>
            <h2 className="text-xl font-semibold text-text-primary">
              Let's get you set up
            </h2>
          </div>

          {/* Card Body */}
          <div className="p-6 space-y-6">
            {/* Website URL Input */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Your Website URL
              </label>
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="url"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://youragency.com"
                  className="w-full pl-10 pr-4 py-3 bg-bg-base border border-border-default rounded-xl
                    text-text-primary placeholder-text-muted
                    focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20
                    transition-all"
                />
              </div>
            </div>

            {/* Auto-provision Notice */}
            <div className="bg-status-success/10 border border-status-success/30 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-5 h-5 bg-status-success/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Check className="w-3 h-3 text-status-success" />
                </div>
                <div>
                  <p className="text-sm font-medium text-status-success">
                    Email &amp; Phone auto-provisioned
                  </p>
                  <p className="text-xs text-text-muted mt-0.5">
                    From our pre-warmed pool for immediate deliverability
                  </p>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border-subtle" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-bg-surface text-text-muted">
                  Connect Your Tools
                </span>
              </div>
            </div>

            {/* Integration Buttons Grid */}
            <div className="grid grid-cols-2 gap-4">
              {/* HubSpot CRM */}
              <button
                onClick={() => setHubspotConnected(!hubspotConnected)}
                className={`
                  relative flex flex-col items-center justify-center p-4 rounded-xl border transition-all
                  ${
                    hubspotConnected
                      ? "bg-status-success/10 border-status-success/30"
                      : "bg-bg-base border-border-default hover:border-border-strong"
                  }
                `}
              >
                <div className="w-10 h-10 bg-[#FF7A59]/15 rounded-lg flex items-center justify-center mb-2">
                  <span className="text-[#FF7A59] font-bold text-sm">H</span>
                </div>
                <span className="text-sm font-medium text-text-primary">
                  HubSpot CRM
                </span>
                {hubspotConnected && (
                  <span className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </span>
                )}
              </button>

              {/* LinkedIn */}
              <button
                onClick={() => setLinkedinConnected(!linkedinConnected)}
                className={`
                  relative flex flex-col items-center justify-center p-4 rounded-xl border transition-all
                  ${
                    linkedinConnected
                      ? "bg-status-success/10 border-status-success/30"
                      : "bg-bg-base border-border-default hover:border-border-strong"
                  }
                `}
              >
                <div className="w-10 h-10 bg-[#0077B5]/15 rounded-lg flex items-center justify-center mb-2">
                  <Linkedin className="w-5 h-5 text-[#0077B5]" />
                </div>
                <span className="text-sm font-medium text-text-primary">
                  LinkedIn
                </span>
                {linkedinConnected && (
                  <span className="absolute top-2 right-2 w-5 h-5 bg-status-success rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </span>
                )}
              </button>
            </div>

            {/* Launch Button */}
            <button
              onClick={handleLaunch}
              className="w-full py-3.5 bg-gradient-to-r from-accent-primary to-accent-blue 
                text-white font-semibold rounded-xl
                hover:opacity-90 transition-opacity
                shadow-glow-sm hover:shadow-glow-md"
            >
              Launch Dashboard →
            </button>
          </div>

          {/* Card Footer */}
          <div className="px-6 py-4 bg-bg-base/50 border-t border-border-subtle">
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
      </div>
    </div>
  );
}
