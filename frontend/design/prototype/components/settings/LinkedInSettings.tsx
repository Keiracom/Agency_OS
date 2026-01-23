"use client";

import { useState } from "react";
import { ArrowLeft, Linkedin, Eye, EyeOff } from "lucide-react";
import { DashboardShell } from "../layout/DashboardShell";
import { LinkedInStatusCard, LinkedInStatus } from "./LinkedInStatusCard";

/**
 * Connection form state
 */
type FormState = "idle" | "form" | "connecting" | "2fa";

/**
 * LinkedInSettings - LinkedIn connection management page
 *
 * Features:
 * - LinkedInStatusCard component
 * - Connection form (when disconnected)
 * - 2FA form (when awaiting verification)
 * - Security information
 *
 * Design tokens from DESIGN_SYSTEM.md applied throughout
 */
export function LinkedInSettings() {
  const [status, setStatus] = useState<LinkedInStatus>("connected");
  const [formState, setFormState] = useState<FormState>("idle");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState("");

  const handleConnect = () => {
    setFormState("form");
  };

  const handleDisconnect = () => {
    setStatus("disconnected");
  };

  const handleSubmitCredentials = (e: React.FormEvent) => {
    e.preventDefault();
    setFormState("connecting");
    // Simulate connection attempt
    setTimeout(() => {
      // Simulate 2FA required
      setFormState("2fa");
    }, 2000);
  };

  const handleSubmit2FA = (e: React.FormEvent) => {
    e.preventDefault();
    setFormState("connecting");
    // Simulate verification
    setTimeout(() => {
      setStatus("connected");
      setFormState("idle");
      setEmail("");
      setPassword("");
      setTwoFactorCode("");
    }, 1500);
  };

  const handleCancel = () => {
    setFormState("idle");
    setEmail("");
    setPassword("");
    setTwoFactorCode("");
  };

  return (
    <DashboardShell title="LinkedIn Settings" activePath="/settings">
      <div className="max-w-2xl mx-auto">
        {/* Back Button */}
        <button
          type="button"
          className="flex items-center gap-2 text-sm text-[#64748B] hover:text-[#1E293B] mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Settings
        </button>

        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-[#1E293B]">
            LinkedIn Settings
          </h1>
          <p className="text-sm text-[#64748B] mt-1">
            Manage your LinkedIn connection for automated outreach
          </p>
        </div>

        {/* Connection Form */}
        {formState === "form" && (
          <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-[#E2E8F0]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-[#0077B5]/10 rounded-lg">
                  <Linkedin className="h-5 w-5 text-[#0077B5]" />
                </div>
                <h3 className="text-sm font-semibold text-[#1E293B]">
                  Connect LinkedIn
                </h3>
              </div>
            </div>
            <form onSubmit={handleSubmitCredentials} className="p-6 space-y-4">
              <p className="text-sm text-[#64748B]">
                Enter your LinkedIn credentials to connect your account
              </p>
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                  placeholder="your.email@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-2.5 pr-12 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                    placeholder="Your LinkedIn password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-[#64748B]"
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#0077B5] hover:bg-[#005C8F] text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Connect
                </button>
              </div>
            </form>
          </div>
        )}

        {/* 2FA Form */}
        {formState === "2fa" && (
          <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-[#E2E8F0]">
              <h3 className="text-sm font-semibold text-[#1E293B]">
                Verification Required
              </h3>
            </div>
            <form onSubmit={handleSubmit2FA} className="p-6 space-y-4">
              <p className="text-sm text-[#64748B]">
                LinkedIn sent a verification code via SMS. Enter the code to complete
                connection.
              </p>
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Verification Code
                </label>
                <input
                  type="text"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent tracking-widest text-center text-lg"
                  placeholder="------"
                  maxLength={6}
                  required
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#0077B5] hover:bg-[#005C8F] text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Verify
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Connecting State */}
        {formState === "connecting" && (
          <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-8 text-center mb-6">
            <div className="w-16 h-16 bg-[#0077B5]/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Linkedin className="h-8 w-8 text-[#0077B5] animate-pulse" />
            </div>
            <p className="text-sm text-[#64748B]">
              Connecting to LinkedIn...
            </p>
          </div>
        )}

        {/* Status Card (when not showing form) */}
        {formState === "idle" && (
          <LinkedInStatusCard
            status={status}
            profileName={status === "connected" ? "John Smith" : null}
            profileUrl={status === "connected" ? "https://linkedin.com/in/johnsmith" : null}
            connectedAt={status === "connected" ? "2026-01-15T14:30:00Z" : null}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
          />
        )}
      </div>
    </DashboardShell>
  );
}

export default LinkedInSettings;
