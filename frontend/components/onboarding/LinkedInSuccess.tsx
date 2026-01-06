/**
 * FILE: frontend/components/onboarding/LinkedInSuccess.tsx
 * PURPOSE: Success state after LinkedIn connection
 * PHASE: 24H - LinkedIn Credential Connection
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface LinkedInSuccessProps {
  profileName?: string | null;
  profileUrl?: string | null;
  onContinue: () => void;
}

export function LinkedInSuccess({
  profileName,
  profileUrl,
  onContinue,
}: LinkedInSuccessProps) {
  return (
    <div className="space-y-6 text-center py-8">
      <div className="space-y-4">
        <SuccessIcon className="mx-auto h-16 w-16 text-green-500" />
        <h3 className="text-lg font-semibold">LinkedIn Connected!</h3>
        <p className="text-muted-foreground text-sm">
          Your LinkedIn account is now connected for automated outreach.
        </p>
      </div>

      {(profileName || profileUrl) && (
        <Card className="max-w-sm mx-auto">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <LinkedInLogo className="h-10 w-10 text-[#0077b5]" />
              <div className="text-left">
                {profileName && (
                  <p className="font-medium">{profileName}</p>
                )}
                {profileUrl && (
                  <a
                    href={profileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline"
                  >
                    View Profile
                  </a>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Agency OS can now:
        </p>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>Send connection requests to prospects</li>
          <li>Send personalized messages</li>
          <li>Follow up with interested leads</li>
        </ul>
      </div>

      <Button onClick={onContinue} className="w-full max-w-xs">
        Continue
      </Button>
    </div>
  );
}

function SuccessIcon({ className }: { className?: string }) {
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
        d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
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

export default LinkedInSuccess;
