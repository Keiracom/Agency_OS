/**
 * FILE: frontend/components/dispatcher/api-key-rotate-dialog.tsx
 * PURPOSE: One-shot plaintext-key display modal for the rotate flow.
 *          The customer sees the new plaintext key EXACTLY ONCE (this dialog
 *          renders); after dismiss, the plaintext is gone from the UI and
 *          can never be retrieved again (server-side encrypted via Orion's
 *          KEI-116 pgcrypto; UI only sees plaintext at create/rotate time).
 * KEI: 160 (KEI-114C) — sibling to api-key-list.tsx.
 *
 * Stub: typed component shell. Sub-KEI claimer wires the actual server-action
 * that POSTs to a /api/dispatcher/keys/rotate handler, receives the plaintext
 * (in the response body, NEVER stored client-side beyond this dialog's lifetime),
 * and triggers re-render with the new plaintext via the `plaintext` prop.
 *
 * The dialog deliberately exposes a "Copy to clipboard" affordance because the
 * customer MUST capture the plaintext before dismissing — otherwise they lose
 * access. After dismiss, this component's `plaintext` prop should be reset to
 * null at the call-site so the value drops out of React state.
 */

import * as React from "react";

import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";

export interface ApiKeyRotateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Plaintext API key — present ONLY for the duration of this dialog. */
  plaintext: string | null;
  /** Label of the rotated key, for display in the description text. */
  label: string;
  /** Called when the customer confirms they've captured the key. */
  onAcknowledge?: () => void;
}

export function ApiKeyRotateDialog({
  open,
  onOpenChange,
  plaintext,
  label,
  onAcknowledge,
}: Readonly<ApiKeyRotateDialogProps>) {
  const handleCopy = React.useCallback(() => {
    if (plaintext === null) return;
    void navigator.clipboard?.writeText(plaintext);
  }, [plaintext]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="api-key-rotate-dialog" className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Save your new API key</DialogTitle>
          <DialogDescription>
            Copy the key below before closing this dialog. We don&apos;t store
            the plaintext — once you dismiss, you cannot retrieve it.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm font-medium">{label}</p>
          {plaintext === null ? (
            <p
              data-testid="api-key-rotate-pending"
              className="rounded-md bg-muted p-3 font-mono text-sm text-muted-foreground"
            >
              Generating…
            </p>
          ) : (
            <pre
              data-testid="api-key-rotate-plaintext"
              className="overflow-x-auto whitespace-pre-wrap break-all rounded-md bg-muted p-3 font-mono text-sm"
            >
              {plaintext}
            </pre>
          )}
        </div>
        <DialogFooter className="gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={plaintext === null}
            onClick={handleCopy}
          >
            Copy to clipboard
          </Button>
          <Button
            type="button"
            disabled={plaintext === null}
            onClick={() => {
              onAcknowledge?.();
              onOpenChange(false);
            }}
          >
            I&apos;ve saved it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
