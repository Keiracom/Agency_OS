/**
 * FILE: frontend/lib/supabase/client.ts
 * PURPOSE: Browser-side Supabase client using @supabase/ssr
 * MIGRATION: Replaces createClientComponentClient from @supabase/auth-helpers-nextjs
 */

import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
