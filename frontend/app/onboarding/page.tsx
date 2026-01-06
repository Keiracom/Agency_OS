/**
 * FILE: frontend/app/onboarding/page.tsx
 * TASK: ICP-015
 * PHASE: 11 (ICP Discovery System)
 * PURPOSE: Onboarding flow for new clients - website input and ICP confirmation
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card';
import {
  Globe,
  Loader2,
  XCircle,
  ChevronRight,
} from 'lucide-react';
import { createClient } from '@/lib/supabase';

export default function OnboardingPage() {
  const router = useRouter();
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Start extraction and redirect to dashboard immediately
  const handleStartExtraction = async () => {
    if (!websiteUrl.trim()) {
      setError('Please enter a website URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      // Debug logging
      console.log('[Onboarding] Session check:', {
        hasSession: !!session,
        sessionError: sessionError?.message,
        tokenPreview: session?.access_token?.substring(0, 50),
        userId: session?.user?.id,
        expiresAt: session?.expires_at,
      });

      if (!session) {
        console.error('[Onboarding] No session found, redirecting to login');
        router.push('/login');
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/onboarding/analyze`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({ website_url: websiteUrl }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start extraction');
      }

      const data = await response.json();

      // Store job_id in localStorage for persistence across refreshes
      localStorage.setItem('icp_job_id', data.job_id);

      // Redirect to dashboard immediately with job_id in URL
      router.push(`/dashboard?icp_job=${data.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  };

  // Render input step
  return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-lg">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Globe className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl">Welcome to Agency OS</CardTitle>
            <CardDescription>
              Enter your website URL and we&apos;ll automatically discover your
              ideal customer profile
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="website">Your Website URL</Label>
              <Input
                id="website"
                type="url"
                placeholder="https://youragency.com"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                disabled={loading}
              />
            </div>
            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <XCircle className="h-4 w-4" />
                {error}
              </div>
            )}
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button
              className="w-full"
              size="lg"
              onClick={handleStartExtraction}
              disabled={loading || !websiteUrl.trim()}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  Discover My ICP
                  <ChevronRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
            <button
              type="button"
              onClick={() => router.push('/onboarding/skip')}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip for now (testing only)
            </button>
          </CardFooter>
        </Card>
      </div>
  );
}
