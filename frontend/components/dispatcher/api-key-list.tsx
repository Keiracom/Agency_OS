/**
 * FILE: frontend/components/dispatcher/api-key-list.tsx
 * PURPOSE: Customer-facing API key list for the Dispatcher dashboard.
 *          Renders existing keys (lookup-hash prefix + label + last_used_at)
 *          and emits rotate / revoke action callbacks. Sub-KEI claimer wires
 *          data loading + server actions for the rotate (encrypt-and-show-once)
 *          + revoke (soft-delete) flows on top of Orion's KEI-116 BYO crypto.
 * KEI: 160 (KEI-114C) — child of Aiden's KEI-114 dashboard scaffold.
 *
 * Stub: typed component shell + props interface. Render path uses the shared
 * shadcn Table + Button primitives. NO plaintext key handling here — keys
 * appear ONCE at create/rotate time via api-key-rotate-dialog.tsx, never again.
 *
 * LAW II: no monetary values on this page (key metadata only); $AUD-only rule
 * does not apply but ApiKeyRow shape stays free of any USD-named field so
 * future "key with attached cost cap" extensions inherit the AUD-first norm.
 *
 * Security shape (load-bearing for sub-KEI claimer):
 *   - DISPLAY field is `lookup_hash_prefix` (first 8 hex chars of SHA-256 hash).
 *   - The plaintext `secret` is NEVER passed into this component. It only
 *     exists on the rotate-dialog momentarily and then must be cleared.
 *   - `last_used_at` is observed via api_keys.last_used_at (KEI-116C lookup
 *     hash table write). Stale-key detection (e.g. >90d unused) lives in a
 *     later sub-KEI, not here.
 */

import * as React from "react";

import { Button } from "../ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";

export interface ApiKey {
  id: string;
  label: string;
  /** First 8 hex chars of SHA-256 lookup hash; full key never returned to UI. */
  lookup_hash_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyListProps {
  keys: ApiKey[];
  loading?: boolean;
  emptyMessage?: string;
  onRotate?: (keyId: string) => void;
  onRevoke?: (keyId: string) => void;
}

const formatTimestamp = (iso: string | null): string =>
  iso === null ? "—" : new Date(iso).toLocaleString();

export function ApiKeyList({
  keys,
  loading = false,
  emptyMessage = "No API keys yet. Generate your first key to get started.",
  onRotate,
  onRevoke,
}: Readonly<ApiKeyListProps>) {
  if (loading) {
    return (
      <div
        data-testid="api-key-list-loading"
        className="py-8 text-center text-sm text-muted-foreground"
      >
        Loading keys…
      </div>
    );
  }
  if (keys.length === 0) {
    return (
      <div
        data-testid="api-key-list-empty"
        className="py-8 text-center text-sm text-muted-foreground"
      >
        {emptyMessage}
      </div>
    );
  }
  return (
    <Table data-testid="api-key-list-table">
      <TableHeader>
        <TableRow>
          <TableHead>Label</TableHead>
          <TableHead>Hash prefix</TableHead>
          <TableHead>Created</TableHead>
          <TableHead>Last used</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {keys.map((k) => {
          const isRevoked = k.revoked_at !== null;
          return (
            <TableRow
              key={k.id}
              data-key-id={k.id}
              data-key-revoked={isRevoked ? "true" : "false"}
            >
              <TableCell className="font-medium">{k.label}</TableCell>
              <TableCell className="font-mono text-xs">
                {k.lookup_hash_prefix}…
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatTimestamp(k.created_at)}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatTimestamp(k.last_used_at)}
              </TableCell>
              <TableCell>{isRevoked ? "Revoked" : "Active"}</TableCell>
              <TableCell className="text-right space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isRevoked || !onRotate}
                  onClick={() => onRotate?.(k.id)}
                >
                  Rotate
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isRevoked || !onRevoke}
                  onClick={() => onRevoke?.(k.id)}
                >
                  Revoke
                </Button>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
