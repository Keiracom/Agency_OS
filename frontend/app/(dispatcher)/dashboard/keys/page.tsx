/**
 * FILE: frontend/app/(dispatcher)/dashboard/keys/page.tsx
 * PURPOSE: API key management — list + rotate + revoke (BYO key flow).
 * KEI: 114C (Linear KEI-160) — Key Mgmt UI implementation.
 *      Deps: 111E (RLS on api_keys), 116A/B/C (BYO key encryption chain —
 *      schema + encrypt/decrypt wrappers + lookup hash, P0 per Max's
 *      DPA-compliance escalation Wave 3 2026-05-17).
 *
 * Stub only. Implementer wires:
 *   - SELECT id, lookup_hash, label, created_at, last_used_at FROM
 *     public.api_keys WHERE tenant_id = current_tenant() — RLS enforces.
 *     NEVER select encrypted_key on this page; display hash prefix only.
 *   - Rotate flow: generate new key (server-side), encrypt-then-store,
 *     return plaintext ONCE (clipboard-copy modal), old key flagged revoked.
 *   - Revoke flow: UPDATE api_keys SET revoked_at = NOW() (soft delete).
 *   - Display: short-hash label (sha256[:8]) so customer can identify the
 *     key without ever seeing the plaintext. Plaintext shown only at
 *     create/rotate time, never again.
 *   - Audit: every rotate/revoke writes to audit_logs (table TBD).
 */

export default function DispatcherDashboardKeysPage() {
  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="text-2xl font-semibold">API keys</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-114C (KEI-160). List + rotate + revoke
        controls land here. Plaintext keys are surfaced once at create/rotate
        time and never again — the list shows lookup-hash prefix only per
        KEI-116 BYO encryption.
      </p>
    </main>
  );
}
