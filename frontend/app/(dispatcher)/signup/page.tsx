/**
 * FILE: frontend/app/(dispatcher)/signup/page.tsx
 * PURPOSE: Dispatcher product signup landing.
 * KEI: 113A (KEI-154) — Aiden/Atlas/Orion implements:
 *      - Supabase signUp + email verification redirect
 *      - emailRedirectTo: /(dispatcher)/verify-email
 *      - on verify success → /(dispatcher)/onboarding/byo-key
 *      - Dep: KEI-111B (auth layer)
 *
 * Stub only.
 */

export default function DispatcherSignupPage() {
  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="text-2xl font-semibold">Sign up for Keiracom</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-113A (KEI-154). Form + Supabase signUp + email
        verification redirect land here. Verified users continue to
        /(dispatcher)/onboarding/byo-key.
      </p>
    </main>
  );
}
