/**
 * FILE: frontend/app/auth/callback/route.ts
 * PURPOSE: Handle Supabase auth callback and redirect based on onboarding status
 * PHASE: 17 (Launch Prerequisites)
 * UPDATED: Auto-provision flow - redirect to onboarding if ICP not confirmed
 */

import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');

  if (code) {
    const cookieStore = await cookies();
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore });
    
    // Exchange code for session
    const { error: sessionError } = await supabase.auth.exchangeCodeForSession(code);
    
    if (sessionError) {
      console.error('Auth callback error:', sessionError);
      return NextResponse.redirect(new URL('/login?error=auth_failed', requestUrl.origin));
    }

    // Check onboarding status
    const { data: onboardingStatus, error: statusError } = await supabase
      .rpc('get_onboarding_status');

    if (statusError) {
      console.error('Onboarding status error:', statusError);
      // If RPC fails, still redirect to dashboard - it will handle the check
      return NextResponse.redirect(new URL('/dashboard', requestUrl.origin));
    }

    // If user needs onboarding (no ICP confirmed), redirect to onboarding
    if (onboardingStatus && onboardingStatus.length > 0 && onboardingStatus[0].needs_onboarding) {
      return NextResponse.redirect(new URL('/onboarding', requestUrl.origin));
    }
  }

  // Default: redirect to dashboard
  return NextResponse.redirect(new URL('/dashboard', requestUrl.origin));
}
