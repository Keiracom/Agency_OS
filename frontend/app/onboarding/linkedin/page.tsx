/**
 * FILE: frontend/app/onboarding/linkedin/page.tsx
 * PURPOSE: LinkedIn connection onboarding page
 * PHASE: 24H - LinkedIn Credential Connection
 */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LinkedInCredentialForm } from "@/components/onboarding/LinkedInCredentialForm";
import { LinkedInTwoFactor } from "@/components/onboarding/LinkedInTwoFactor";
import { LinkedInConnecting } from "@/components/onboarding/LinkedInConnecting";
import { LinkedInSuccess } from "@/components/onboarding/LinkedInSuccess";
import {
  useLinkedInConnect,
  useLinkedInVerify2FA,
  useLinkedInStatus,
} from "@/hooks/use-linkedin";

type ConnectionState = "form" | "connecting" | "2fa" | "success" | "error";

export default function LinkedInOnboardingPage() {
  const router = useRouter();
  const [state, setState] = useState<ConnectionState>("form");
  const [error, setError] = useState<string | null>(null);
  const [twoFactorMethod, setTwoFactorMethod] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<{
    name?: string | null;
    url?: string | null;
  }>({});

  const { data: statusData, refetch: refetchStatus } = useLinkedInStatus();
  const connectMutation = useLinkedInConnect();
  const verify2FAMutation = useLinkedInVerify2FA();

  // Check if already connected on mount
  useEffect(() => {
    if (statusData?.status === "connected") {
      setProfileData({
        name: statusData.profile_name,
        url: statusData.profile_url,
      });
      setState("success");
    }
  }, [statusData]);

  const handleConnect = async (email: string, password: string) => {
    setError(null);
    setState("connecting");

    try {
      const result = await connectMutation.mutateAsync({ linkedin_email: email, linkedin_password: password });

      if (result.status === "connected") {
        setProfileData({
          name: result.profile_name,
          url: result.profile_url,
        });
        setState("success");
      } else if (result.status === "awaiting_2fa") {
        setTwoFactorMethod(result.method || null);
        setState("2fa");
      } else if (result.status === "failed") {
        setError(result.error || "Connection failed. Please try again.");
        setState("form");
      } else {
        // Still connecting - poll for status
        pollForCompletion();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
      setState("form");
    }
  };

  const handleSubmit2FA = async (code: string) => {
    setError(null);

    try {
      const result = await verify2FAMutation.mutateAsync({ code });

      if (result.status === "connected") {
        setProfileData({
          name: result.profile_name,
          url: result.profile_url,
        });
        setState("success");
      } else if (result.status === "failed") {
        setError(result.error || "Verification failed. Please try again.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    }
  };

  const pollForCompletion = async () => {
    // Poll status every 2 seconds for up to 60 seconds
    const maxAttempts = 30;
    let attempts = 0;

    const poll = async () => {
      attempts++;
      const { data } = await refetchStatus();

      if (data?.status === "connected") {
        setProfileData({
          name: data.profile_name,
          url: data.profile_url,
        });
        setState("success");
        return;
      }

      if (data?.status === "awaiting_2fa") {
        setTwoFactorMethod(data.two_fa_method || null);
        setState("2fa");
        return;
      }

      if (data?.status === "failed") {
        setError(data.error || "Connection failed");
        setState("form");
        return;
      }

      if (attempts < maxAttempts) {
        setTimeout(poll, 2000);
      } else {
        setError("Connection timed out. Please try again.");
        setState("form");
      }
    };

    setTimeout(poll, 2000);
  };

  const handleContinue = () => {
    // Navigate to next onboarding step or dashboard
    router.push("/dashboard");
  };

  const handleSkip = () => {
    // Skip LinkedIn connection for now
    router.push("/dashboard");
  };

  const handleBack = () => {
    setState("form");
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Connect LinkedIn</CardTitle>
          <CardDescription>
            Connect your LinkedIn account to enable automated outreach
          </CardDescription>
        </CardHeader>

        <CardContent>
          {state === "form" && (
            <div className="space-y-6">
              <LinkedInCredentialForm
                onSubmit={handleConnect}
                error={error}
                isLoading={connectMutation.isPending}
              />

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">
                    Or
                  </span>
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={handleSkip}
              >
                Skip for now
              </Button>

              <p className="text-xs text-center text-muted-foreground">
                You can connect LinkedIn later from Settings
              </p>
            </div>
          )}

          {state === "connecting" && (
            <LinkedInConnecting message="Connecting to LinkedIn..." />
          )}

          {state === "2fa" && (
            <LinkedInTwoFactor
              method={twoFactorMethod}
              onSubmit={handleSubmit2FA}
              onBack={handleBack}
              error={error}
              isLoading={verify2FAMutation.isPending}
            />
          )}

          {state === "success" && (
            <LinkedInSuccess
              profileName={profileData.name}
              profileUrl={profileData.url}
              onContinue={handleContinue}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
