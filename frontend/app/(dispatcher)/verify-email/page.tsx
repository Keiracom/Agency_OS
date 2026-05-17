/**
 * FILE: frontend/app/(dispatcher)/verify-email/page.tsx
 * PURPOSE: Email-verification waiting / confirm landing page.
 * KEI: 113A (KEI-154) — pairs with signup; renders the "check your email"
 *      state. The actual verify callback lives at /auth/callback (shared).
 *      On successful verify, redirect to /(dispatcher)/onboarding/byo-key.
 *
 * Stub only.
 */

export default function DispatcherVerifyEmailPage() {
  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="text-2xl font-semibold">Check your email</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-113A. Renders the "verify your email" prompt;
        polls / receives the verified state; redirects to BYO-key onboarding.
      </p>
    </main>
  );
}
