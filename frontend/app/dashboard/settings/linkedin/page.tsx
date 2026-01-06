/**
 * FILE: frontend/app/dashboard/settings/linkedin/page.tsx
 * PURPOSE: LinkedIn connection settings page
 * PHASE: 24H - LinkedIn Credential Connection
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { LinkedInCredentialForm } from "@/components/onboarding/LinkedInCredentialForm";
import { LinkedInTwoFactor } from "@/components/onboarding/LinkedInTwoFactor";
import { LinkedInConnecting } from "@/components/onboarding/LinkedInConnecting";
import {
  useLinkedInStatus,
  useLinkedInConnect,
  useLinkedInVerify2FA,
  useLinkedInDisconnect,
} from "@/hooks/use-linkedin";

type ConnectionState = "idle" | "form" | "connecting" | "2fa";

export default function LinkedInSettingsPage() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [twoFactorMethod, setTwoFactorMethod] = useState<string | null>(null);

  const { data: status, isLoading: statusLoading, refetch } = useLinkedInStatus();
  const connectMutation = useLinkedInConnect();
  const verify2FAMutation = useLinkedInVerify2FA();
  const disconnectMutation = useLinkedInDisconnect();

  const handleConnect = async (email: string, password: string) => {
    setError(null);
    setState("connecting");

    try {
      const result = await connectMutation.mutateAsync({ linkedin_email: email, linkedin_password: password });

      if (result.status === "connected") {
        setState("idle");
        refetch();
      } else if (result.status === "awaiting_2fa") {
        setTwoFactorMethod(result.method || null);
        setState("2fa");
      } else if (result.status === "failed") {
        setError(result.error || "Connection failed");
        setState("form");
      } else {
        // Poll for completion
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
        setState("idle");
        refetch();
      } else if (result.status === "failed") {
        setError(result.error || "Verification failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnectMutation.mutateAsync();
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
    }
  };

  const pollForCompletion = async () => {
    const maxAttempts = 30;
    let attempts = 0;

    const poll = async () => {
      attempts++;
      const { data } = await refetch();

      if (data?.status === "connected") {
        setState("idle");
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
        setError("Connection timed out");
        setState("form");
      }
    };

    setTimeout(poll, 2000);
  };

  const getStatusBadge = () => {
    if (statusLoading) {
      return <Badge variant="outline">Loading...</Badge>;
    }

    if (status?.status === "connected") {
      return <Badge className="bg-green-500">Connected</Badge>;
    }

    if (status?.status === "awaiting_2fa") {
      return <Badge variant="secondary">2FA Required</Badge>;
    }

    if (status?.status === "connecting") {
      return <Badge variant="secondary">Connecting...</Badge>;
    }

    return <Badge variant="outline">Not Connected</Badge>;
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <div className="container max-w-2xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">LinkedIn Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your LinkedIn connection for automated outreach
        </p>
      </div>

      {/* Connection Status Card */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Connection Status</CardTitle>
            {getStatusBadge()}
          </div>
        </CardHeader>
        <CardContent>
          {status?.status === "connected" ? (
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
                <LinkedInLogo className="h-12 w-12 text-[#0077b5]" />
                <div className="flex-1">
                  {status.profile_name && (
                    <p className="font-medium">{status.profile_name}</p>
                  )}
                  {status.profile_url && (
                    <a
                      href={status.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View Profile
                    </a>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Connected on {formatDate(status.connected_at)}
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline" className="text-red-600 hover:text-red-700">
                      Disconnect
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Disconnect LinkedIn?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will remove your LinkedIn credentials and stop all automated
                        outreach. You can reconnect at any time.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleDisconnect}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        Disconnect
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>

                <Button variant="outline" onClick={() => setState("form")}>
                  Reconnect
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-muted-foreground mb-4">
                Connect your LinkedIn account to enable automated outreach to prospects.
              </p>
              <Button onClick={() => setState("form")}>
                Connect LinkedIn
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connection Form Modal */}
      {state !== "idle" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {state === "form" && "Connect LinkedIn"}
              {state === "connecting" && "Connecting..."}
              {state === "2fa" && "Verification Required"}
            </CardTitle>
            <CardDescription>
              {state === "form" && "Enter your LinkedIn credentials to connect"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {state === "form" && (
              <div className="space-y-4">
                <LinkedInCredentialForm
                  onSubmit={handleConnect}
                  error={error}
                  isLoading={connectMutation.isPending}
                />
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => {
                    setState("idle");
                    setError(null);
                  }}
                >
                  Cancel
                </Button>
              </div>
            )}

            {state === "connecting" && (
              <LinkedInConnecting />
            )}

            {state === "2fa" && (
              <LinkedInTwoFactor
                method={twoFactorMethod}
                onSubmit={handleSubmit2FA}
                onBack={() => {
                  setState("form");
                  setError(null);
                }}
                error={error}
                isLoading={verify2FAMutation.isPending}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Security Info */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">Security Information</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-green-500" />
              Credentials are encrypted using AES-256 encryption
            </li>
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-green-500" />
              Your password is never stored in plain text
            </li>
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-green-500" />
              Credentials are only used for automated outreach
            </li>
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-green-500" />
              We never post to your LinkedIn feed
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function LinkedInLogo({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className}
    >
      <path
        fillRule="evenodd"
        d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
        clipRule="evenodd"
      />
    </svg>
  );
}
