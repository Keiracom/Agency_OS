/**
 * FILE: frontend/app/(dispatcher)/dashboard/keys/page.tsx
 * PURPOSE: API key management — list + rotate + revoke (BYO key flow).
 * KEI: 160 (KEI-114C) — Key Mgmt UI implementation. Replaces the KEI-114
 *      scaffold stub. Wires the render-component family (api-key-list.tsx +
 *      api-key-rotate-dialog.tsx) on top of mock data; sub-KEI claimer
 *      wires the real Supabase RLS + Orion's KEI-116 BYO crypto on top.
 *
 * Render-path-only (matches Scout's KEI-158 PR #957 pattern): mock data
 * inline, action callbacks log to console. Sub-KEI claimer:
 *   - Replace `_mockKeys` with `useApiKeys()` hook reading public.api_keys
 *     under RLS (sees only the signed-in tenant's rows).
 *   - Replace `onRotate` with a server-action calling /api/dispatcher/keys/
 *     rotate which generates a key, encrypts via pgp_sym_encrypt (KEI-116B),
 *     writes lookup_hash via SHA-256 (KEI-116C), returns plaintext ONCE.
 *   - Replace `onRevoke` with a server-action UPDATE-ing revoked_at=NOW().
 *   - Audit log writes on every rotate/revoke (table TBD).
 *
 * Display contract (load-bearing):
 *   - Plaintext only surfaces inside ApiKeyRotateDialog after a successful
 *     rotate. The dialog's plaintext prop must be reset to null at close.
 *   - lookup_hash_prefix is the only key-identifier shown in the list.
 */

"use client";

import * as React from "react";

import {
  ApiKeyList,
  type ApiKey,
} from "@/components/dispatcher/api-key-list";
import { ApiKeyRotateDialog } from "@/components/dispatcher/api-key-rotate-dialog";

const _mockKeys: ApiKey[] = [
  {
    id: "key-1",
    label: "production",
    lookup_hash_prefix: "a3f8b2c0",
    created_at: "2026-05-01T10:00:00Z",
    last_used_at: "2026-05-17T09:15:00Z",
    revoked_at: null,
  },
];

export default function DispatcherDashboardKeysPage() {
  const [rotateOpen, setRotateOpen] = React.useState(false);
  const [rotatingLabel, setRotatingLabel] = React.useState("");

  const handleRotate = React.useCallback((keyId: string) => {
    const key = _mockKeys.find((k) => k.id === keyId);
    setRotatingLabel(key?.label ?? "");
    setRotateOpen(true);
  }, []);

  const handleRevoke = React.useCallback((keyId: string) => {
    // Sub-KEI claimer: server action UPDATE api_keys SET revoked_at = NOW().
    // eslint-disable-next-line no-console
    console.info("[stub] revoke", keyId);
  }, []);

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">API keys</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Keys appear once at create / rotate time and never again — copy the
          plaintext immediately. The list below shows lookup-hash prefixes
          only.
        </p>
      </header>
      <ApiKeyList
        keys={_mockKeys}
        onRotate={handleRotate}
        onRevoke={handleRevoke}
      />
      <ApiKeyRotateDialog
        open={rotateOpen}
        onOpenChange={setRotateOpen}
        plaintext={null}
        label={rotatingLabel}
      />
    </main>
  );
}
