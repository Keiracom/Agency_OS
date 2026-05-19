/**
 * FILE: frontend/app/dispatcher/onboarding/byo-key/page.tsx
 * PURPOSE: Customer enters their own Anthropic/OpenAI API key.
 * KEI: 113B (KEI-155) — wires:
 *      - Controlled form: provider select + key input
 *      - POST /api/v1/dispatcher/byo-key (pgcrypto pgp_sym_encrypt server-side)
 *      - Plaintext cleared from React state on success — never persists in DOM
 *      - On 201 → /dispatcher/onboarding/first-task
 *      - Backend: src/api/routes/customer_api_keys.py wrapping
 *        src/security/customer_api_keys.store_key (KEI-116A/B/C).
 */

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { APIError, api } from "@/lib/api";

type Provider = "anthropic" | "openai";

export default function DispatcherByoKeyPage() {
  const router = useRouter();
  const [provider, setProvider] = useState<Provider>("anthropic");
  const [plaintext, setPlaintext] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const inFlight = plaintext;
    try {
      await api.post("/api/v1/dispatcher/byo-key", {
        provider,
        plaintext: inFlight,
      });
      setPlaintext("");
      router.push("/dispatcher/onboarding/first-task");
    } catch (err) {
      const msg =
        err instanceof APIError
          ? `Could not store key (${err.status}). Check the key and try again.`
          : "Could not store key. Check your connection and try again.";
      setError(msg);
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="text-2xl font-semibold">Add your API key</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        We encrypt it on store (pgcrypto pgp_sym_encrypt). Plaintext is never written to disk.
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <label className="block">
          <span className="text-sm font-medium">Provider</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as Provider)}
            className="mt-1 w-full rounded border px-3 py-2"
            disabled={submitting}
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
          </select>
        </label>
        <label className="block">
          <span className="text-sm font-medium">API key</span>
          <input
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={plaintext}
            onChange={(e) => setPlaintext(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm"
            placeholder="sk-..."
            minLength={8}
            required
            disabled={submitting}
          />
        </label>
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          className="w-full rounded bg-black px-4 py-2 text-white disabled:opacity-50"
          disabled={submitting || plaintext.length < 8}
        >
          {submitting ? "Storing…" : "Store key and continue"}
        </button>
      </form>
    </main>
  );
}
