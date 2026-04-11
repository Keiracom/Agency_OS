/**
 * FILE: frontend/app/dashboard/settings/linkedin/page.tsx
 * PURPOSE: LinkedIn connection settings page
 * PHASE: 309 - Onboarding Rebuild
 *
 * Credential-based LinkedIn (email/password + 2FA) is deprecated.
 * Connection is now via Unipile OAuth — GET /api/v1/linkedin/connect.
 */

"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
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
import { useLinkedInStatus, useLinkedInDisconnect } from "@/hooks/use-linkedin";

export default function LinkedInSettingsPage() {
  const [error, setError] = useState<string | null>(null);

  const { data: status, isLoading: statusLoading, refetch } = useLinkedInStatus();
  const disconnectMutation = useLinkedInDisconnect();

  const handleConnect = () => {
    // Redirect to Unipile OAuth via backend — backend returns the hosted auth URL
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/linkedin/connect`;
  };

  const handleDisconnect = async () => {
    try {
      await disconnectMutation.mutateAsync();
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
    }
  };

  const getStatusBadge = () => {
    if (statusLoading) {
      return <Badge variant="outline">Loading...</Badge>;
    }

    if (status?.status === "connected") {
      return <Badge className="bg-amber">Connected</Badge>;
    }

    if (status?.status === "connecting") {
      return <Badge variant="secondary">Connecting...</Badge>;
    }

    return <Badge variant="outline">Not Connected</Badge>;
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString("en-AU", {
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

      {error && (
        <div className="mb-4 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Connection Status Card */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Connection Status</CardTitle>
            {getStatusBadge()}
          </div>
          <CardDescription>
            Connect via secure OAuth — no password stored
          </CardDescription>
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
                      className="text-sm text-text-secondary hover:underline"
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
                    <Button variant="outline" className="text-amber hover:text-error">
                      Disconnect
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Disconnect LinkedIn?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will remove your LinkedIn connection and stop all
                        automated outreach. You can reconnect at any time.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleDisconnect}
                        className="bg-amber hover:bg-error"
                      >
                        Disconnect
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>

                <Button variant="outline" onClick={handleConnect}>
                  Reconnect
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-muted-foreground mb-4">
                Connect your LinkedIn account to enable automated outreach to
                prospects. Uses secure OAuth — no password required.
              </p>
              <Button onClick={handleConnect}>Connect LinkedIn</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Security Info */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">Security Information</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-amber" />
              Secure OAuth connection — your password is never stored
            </li>
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-amber" />
              Connection is only used for automated outreach
            </li>
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-amber" />
              We never post to your LinkedIn feed
            </li>
            <li className="flex items-center gap-2">
              <ShieldIcon className="h-4 w-4 text-amber" />
              Disconnect anytime from this page
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
