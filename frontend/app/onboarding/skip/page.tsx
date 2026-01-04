/**
 * FILE: frontend/app/onboarding/skip/page.tsx
 * PURPOSE: Skip onboarding for testing (marks ICP as confirmed with defaults)
 * PHASE: 17 (Launch Prerequisites)
 * NOTE: This is for testing only - can be removed in production
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, SkipForward, AlertTriangle } from 'lucide-react';
import { createClient } from '@/lib/supabase';

export default function SkipOnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSkip = async () => {
    setLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        router.push('/login');
        return;
      }

      // Get user's client
      const { data: onboardingStatus } = await supabase.rpc('get_onboarding_status');
      
      if (!onboardingStatus || onboardingStatus.length === 0) {
        setError('No client found. Please sign up first.');
        return;
      }

      const clientId = onboardingStatus[0].client_id;

      // Update client with default ICP values and mark as confirmed
      const { error: updateError } = await supabase
        .from('clients')
        .update({
          icp_industries: ['professional_services', 'technology', 'healthcare'],
          icp_company_sizes: ['11-50', '51-200'],
          icp_locations: ['Australia'],
          icp_titles: ['CEO', 'Founder', 'Managing Director', 'Marketing Director'],
          icp_pain_points: ['Lead generation', 'Client acquisition', 'Pipeline growth'],
          value_proposition: 'We help businesses grow through effective marketing',
          services_offered: ['Digital Marketing', 'Lead Generation', 'Content Marketing'],
          icp_confirmed_at: new Date().toISOString(),
          icp_extraction_source: 'manual_skip',
        })
        .eq('id', clientId);

      if (updateError) {
        setError(updateError.message);
        return;
      }

      // Redirect to dashboard
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-yellow-100">
            <AlertTriangle className="h-8 w-8 text-yellow-600" />
          </div>
          <CardTitle className="text-2xl">Skip Onboarding</CardTitle>
          <CardDescription>
            This will set default ICP values and skip the website analysis.
            Use this only for testing purposes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><strong>Default values will be set:</strong></p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Industries: Professional Services, Technology, Healthcare</li>
              <li>Company sizes: 11-50, 51-200</li>
              <li>Location: Australia</li>
              <li>Titles: CEO, Founder, MD, Marketing Director</li>
            </ul>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => router.push('/onboarding')}
            >
              Go Back
            </Button>
            <Button
              className="flex-1"
              onClick={handleSkip}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Skipping...
                </>
              ) : (
                <>
                  <SkipForward className="mr-2 h-4 w-4" />
                  Skip & Continue
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
