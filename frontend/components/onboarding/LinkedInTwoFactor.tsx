/**
 * FILE: frontend/components/onboarding/LinkedInTwoFactor.tsx
 * PURPOSE: 2FA code input for LinkedIn connection
 * PHASE: 24H - LinkedIn Credential Connection
 */

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface LinkedInTwoFactorProps {
  method?: string | null;
  onSubmit: (code: string) => void;
  onBack?: () => void;
  error?: string | null;
  isLoading?: boolean;
}

export function LinkedInTwoFactor({
  method,
  onSubmit,
  onBack,
  error,
  isLoading = false,
}: LinkedInTwoFactorProps) {
  const [code, setCode] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length >= 4) {
      onSubmit(code);
    }
  };

  const getMethodDescription = () => {
    switch (method?.toLowerCase()) {
      case "sms":
        return "LinkedIn sent a code to your phone.";
      case "email":
        return "LinkedIn sent a code to your email.";
      case "authenticator":
        return "Open your authenticator app for the code.";
      default:
        return "LinkedIn sent you a verification code.";
    }
  };

  return (
    <div className="space-y-6 text-center">
      <div className="space-y-2">
        <PhoneIcon className="mx-auto h-12 w-12 text-blue-500" />
        <h3 className="text-lg font-semibold">Verification Required</h3>
        <p className="text-muted-foreground text-sm">
          {getMethodDescription()}
          <br />
          Enter the code below to complete connection.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={8}
          placeholder="000000"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          disabled={isLoading}
          className="text-center text-2xl tracking-widest font-mono"
          autoFocus
        />

        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-2">
          <Button
            type="submit"
            className="w-full"
            disabled={isLoading || code.length < 4}
          >
            {isLoading ? "Verifying..." : "Verify Code"}
          </Button>

          {onBack && (
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={onBack}
              disabled={isLoading}
            >
              Back to Login
            </Button>
          )}
        </div>
      </form>

      <p className="text-xs text-muted-foreground">
        Code not received? Check your spam folder or try again in a few minutes.
      </p>
    </div>
  );
}

function PhoneIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className={className}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3"
      />
    </svg>
  );
}

export default LinkedInTwoFactor;
