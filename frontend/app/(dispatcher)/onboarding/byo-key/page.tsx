/**
 * FILE: frontend/app/(dispatcher)/onboarding/byo-key/page.tsx
 * PURPOSE: Customer enters their own Anthropic/OpenAI API key.
 * KEI: 113B (KEI-155) — implements:
 *      - Form: API key input + provider select
 *      - On submit: POST → backend endpoint that pgp_sym_encrypts via
 *        pgcrypto + stores encrypted_key + SHA-256 lookup hash
 *      - Plaintext NEVER persisted; cleared from React state post-submit
 *      - Deps: KEI-116A pgcrypto schema (KEI-167), KEI-116B encrypt-on-insert (KEI-168),
 *        KEI-116C SHA-256 lookup hash (KEI-169)
 *      - On success → /(dispatcher)/onboarding/first-task
 *
 * Stub only.
 */

export default function DispatcherByoKeyPage() {
  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="text-2xl font-semibold">Add your API key</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-113B (KEI-155). Customer pastes their Anthropic
        or OpenAI key; backend encrypts via pgp_sym_encrypt (KEI-116A/B/C schema);
        plaintext never persisted; advance to first-task.
      </p>
    </main>
  );
}
