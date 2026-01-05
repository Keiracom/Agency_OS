/**
 * FILE: frontend/app/onboarding/page.tsx
 * TASK: ICP-015
 * PHASE: 11 (ICP Discovery System)
 * PURPOSE: Onboarding flow for new clients - website input and ICP confirmation
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import {
  Globe,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronRight,
  Building2,
  Target,
  Users,
  Briefcase,
  MapPin,
  TrendingUp,
} from 'lucide-react';
import { createClient } from '@/lib/supabase';

interface ExtractionStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_step: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  error_message: string | null;
}

interface ICPProfile {
  company_name: string;
  website_url: string;
  company_description: string;
  services_offered: string[];
  primary_service_categories: string[];
  value_proposition: string;
  taglines: string[];
  differentiators: string[];
  team_size: number | null;
  size_range: string;
  years_in_business: number | null;
  portfolio_companies: string[];
  notable_brands: string[];
  icp_industries: string[];
  icp_company_sizes: string[];
  icp_revenue_ranges: string[];
  icp_locations: string[];
  icp_titles: string[];
  icp_pain_points: string[];
  icp_signals: string[];
  als_weights: Record<string, number>;
  pattern_description: string;
  confidence: number;
}

type OnboardingStep = 'input' | 'analyzing' | 'review' | 'complete';

const EXTRACTION_STEPS = [
  'Scraping website',
  'Parsing content',
  'Extracting services',
  'Finding portfolio',
  'Classifying industries',
  'Estimating company size',
  'Deriving ICP pattern',
  'Suggesting ALS weights',
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<OnboardingStep>('input');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ExtractionStatus | null>(null);
  const [profile, setProfile] = useState<ICPProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);

  // Poll for extraction status
  const pollStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) return;

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/onboarding/status/${jobId}`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to get status');

      const statusData: ExtractionStatus = await response.json();
      setStatus(statusData);

      if (statusData.status === 'completed') {
        // Fetch the result
        const resultResponse = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/onboarding/result/${jobId}`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

        if (resultResponse.ok) {
          const profileData: ICPProfile = await resultResponse.json();
          setProfile(profileData);
          setStep('review');
        }
      } else if (statusData.status === 'failed') {
        setError(statusData.error_message || 'Extraction failed');
        setStep('input');
      }
    } catch (err) {
      console.error('Poll error:', err);
    }
  }, [jobId]);

  // Set up polling
  useEffect(() => {
    if (step !== 'analyzing' || !jobId) return;

    const interval = setInterval(pollStatus, 2000);
    return () => clearInterval(interval);
  }, [step, jobId, pollStatus]);

  // Start extraction
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
      setJobId(data.job_id);
      setStep('analyzing');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  // Confirm ICP
  const handleConfirmICP = async () => {
    if (!jobId) return;

    setConfirmLoading(true);

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        router.push('/login');
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/onboarding/confirm`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({ job_id: jobId }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to confirm ICP');
      }

      setStep('complete');
      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        router.push('/dashboard');
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setConfirmLoading(false);
    }
  };

  // Render input step
  if (step === 'input') {
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

  // Render analyzing step
  if (step === 'analyzing') {
    const currentStepIndex = status?.completed_steps || 0;
    const progress = status?.progress_percent || 0;

    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-lg">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Loader2 className="h-8 w-8 text-primary animate-spin" />
            </div>
            <CardTitle className="text-2xl">Analyzing Your Website</CardTitle>
            <CardDescription>
              This usually takes 1-2 minutes. We&apos;re extracting your ideal
              customer profile...
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium">{Math.round(progress)}%</span>
              </div>
              <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Steps */}
            <div className="space-y-2">
              {EXTRACTION_STEPS.map((stepName, index) => {
                const isComplete = index < currentStepIndex;
                const isCurrent = index === currentStepIndex;

                return (
                  <div
                    key={stepName}
                    className={`flex items-center gap-3 p-2 rounded-lg ${
                      isCurrent
                        ? 'bg-primary/10'
                        : isComplete
                        ? 'text-muted-foreground'
                        : 'text-muted-foreground/50'
                    }`}
                  >
                    {isComplete ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : isCurrent ? (
                      <Loader2 className="h-4 w-4 text-primary animate-spin" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-muted" />
                    )}
                    <span className={isCurrent ? 'font-medium' : ''}>
                      {stepName}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Render review step
  if (step === 'review' && profile) {
    return (
      <div className="min-h-screen bg-background p-4 md:p-8">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h1 className="text-3xl font-bold">ICP Extracted!</h1>
            <p className="text-muted-foreground mt-2">
              Review your ideal customer profile below. You can adjust these
              settings later.
            </p>
          </div>

          {/* Company Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-primary" />
                <CardTitle>Your Agency</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-muted-foreground">Company Name</Label>
                  <p className="font-medium">{profile.company_name}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Team Size</Label>
                  <p className="font-medium">
                    {profile.team_size
                      ? `~${profile.team_size} employees`
                      : profile.size_range}
                  </p>
                </div>
              </div>
              <div>
                <Label className="text-muted-foreground">Value Proposition</Label>
                <p className="mt-1">{profile.value_proposition}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Services</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {profile.services_offered.slice(0, 8).map((service) => (
                    <Badge key={service} variant="secondary">
                      {service}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ICP Profile */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Target className="h-5 w-5 text-primary" />
                <CardTitle>Ideal Customer Profile</CardTitle>
              </div>
              <CardDescription>
                {profile.pattern_description}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Industries */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Briefcase className="h-4 w-4 text-muted-foreground" />
                    <Label>Target Industries</Label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {profile.icp_industries.map((industry) => (
                      <Badge key={industry} variant="outline">
                        {industry.replace(/_/g, ' ')}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Company Sizes */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <Label>Company Sizes</Label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {profile.icp_company_sizes.map((size) => (
                      <Badge key={size} variant="outline">
                        {size} employees
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Locations */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <Label>Target Locations</Label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {profile.icp_locations.map((location) => (
                      <Badge key={location} variant="outline">
                        {location}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Titles */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    <Label>Target Titles</Label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {profile.icp_titles.slice(0, 5).map((title) => (
                      <Badge key={title} variant="outline">
                        {title}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              {/* Pain Points */}
              {profile.icp_pain_points.length > 0 && (
                <div>
                  <Label className="mb-2 block">Pain Points</Label>
                  <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                    {profile.icp_pain_points.slice(0, 4).map((pain) => (
                      <li key={pain}>{pain}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Confidence */}
              <div className="flex items-center gap-4 pt-4 border-t">
                <span className="text-sm text-muted-foreground">
                  Extraction Confidence:
                </span>
                <Badge
                  variant={
                    profile.confidence >= 0.8
                      ? 'default'
                      : profile.confidence >= 0.6
                      ? 'secondary'
                      : 'outline'
                  }
                >
                  {Math.round(profile.confidence * 100)}%
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-between items-center pt-4">
            <Button variant="outline" onClick={() => setStep('input')}>
              Start Over
            </Button>
            <Button size="lg" onClick={handleConfirmICP} disabled={confirmLoading}>
              {confirmLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  Confirm & Continue
                  <ChevronRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Render complete step
  if (step === 'complete') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-lg text-center">
          <CardHeader>
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl">You&apos;re All Set!</CardTitle>
            <CardDescription>
              Your ICP has been saved. Redirecting to dashboard...
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
}
