/**
 * FILE: frontend/components/onboarding/LinkedInCredentialForm.tsx
 * PURPOSE: LinkedIn credential input form for onboarding
 * PHASE: 24H - LinkedIn Credential Connection
 */

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

interface LinkedInCredentialFormProps {
  onSubmit: (email: string, password: string) => void;
  error?: string | null;
  isLoading?: boolean;
}

export function LinkedInCredentialForm({
  onSubmit,
  error,
  isLoading = false,
}: LinkedInCredentialFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email && password) {
      onSubmit(email, password);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="linkedin-email">LinkedIn Email</Label>
          <Input
            id="linkedin-email"
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="linkedin-password">LinkedIn Password</Label>
          <Input
            id="linkedin-password"
            type="password"
            placeholder="Your LinkedIn password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            required
          />
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      <SecurityNotice />

      <Button type="submit" className="w-full" disabled={isLoading || !email || !password}>
        {isLoading ? "Connecting..." : "Connect LinkedIn"}
      </Button>
    </form>
  );
}

function SecurityNotice() {
  return (
    <Card className="bg-blue-50 border-blue-200">
      <CardContent className="p-4">
        <h4 className="font-medium text-blue-900 mb-2">
          Your credentials are secure
        </h4>
        <ul className="space-y-1 text-sm text-blue-700">
          <li className="flex items-center gap-2">
            <CheckIcon className="h-4 w-4 text-blue-500 flex-shrink-0" />
            Encrypted at rest using AES-256
          </li>
          <li className="flex items-center gap-2">
            <CheckIcon className="h-4 w-4 text-blue-500 flex-shrink-0" />
            Only used for outreach automation
          </li>
          <li className="flex items-center gap-2">
            <CheckIcon className="h-4 w-4 text-blue-500 flex-shrink-0" />
            We never post to your feed
          </li>
          <li className="flex items-center gap-2">
            <CheckIcon className="h-4 w-4 text-blue-500 flex-shrink-0" />
            Disconnect anytime from settings
          </li>
        </ul>
      </CardContent>
    </Card>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className}
    >
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default LinkedInCredentialForm;
