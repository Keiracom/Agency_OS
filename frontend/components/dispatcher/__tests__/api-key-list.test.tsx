/**
 * Tests for ApiKeyList + ApiKeyRotateDialog component shells (KEI-160).
 *
 * Render-path-only — sub-KEI claimer extends with server-action tests once
 * the encrypt-and-show-once + revoke wires land on top of Orion's KEI-116
 * BYO crypto.
 */

import { describe, expect, test, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { ApiKeyList, type ApiKey } from "../api-key-list";
import { ApiKeyRotateDialog } from "../api-key-rotate-dialog";

const _sample: ApiKey[] = [
  {
    id: "key-1",
    label: "production",
    lookup_hash_prefix: "a3f8b2c0",
    created_at: "2026-05-01T10:00:00Z",
    last_used_at: "2026-05-17T09:15:00Z",
    revoked_at: null,
  },
  {
    id: "key-2",
    label: "ci-pipeline",
    lookup_hash_prefix: "9e1d4f77",
    created_at: "2026-04-12T08:30:00Z",
    last_used_at: null,
    revoked_at: null,
  },
  {
    id: "key-3",
    label: "old-key",
    lookup_hash_prefix: "11abcd22",
    created_at: "2026-03-01T08:30:00Z",
    last_used_at: "2026-04-30T22:00:00Z",
    revoked_at: "2026-05-10T11:00:00Z",
  },
];

describe("ApiKeyList", () => {
  test("renders empty-state when keys=[]", () => {
    render(<ApiKeyList keys={[]} />);
    expect(screen.getByTestId("api-key-list-empty")).toBeInTheDocument();
  });

  test("renders loading-state when loading=true", () => {
    render(<ApiKeyList keys={[]} loading />);
    expect(screen.getByTestId("api-key-list-loading")).toBeInTheDocument();
  });

  test("renders table with one row per key", () => {
    render(<ApiKeyList keys={_sample} />);
    const table = screen.getByTestId("api-key-list-table");
    expect(table).toBeInTheDocument();
    expect(screen.getByText("production")).toBeInTheDocument();
    expect(screen.getByText("ci-pipeline")).toBeInTheDocument();
    expect(screen.getByText("old-key")).toBeInTheDocument();
  });

  test("renders hash prefix with ellipsis (never plaintext)", () => {
    render(<ApiKeyList keys={_sample} />);
    expect(screen.getByText("a3f8b2c0…")).toBeInTheDocument();
    expect(screen.getByText("9e1d4f77…")).toBeInTheDocument();
  });

  test("shows '—' for keys never used", () => {
    render(<ApiKeyList keys={[_sample[1]]} />);
    // never-used row renders em-dash in the last-used cell
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(1);
  });

  test("revoked key shows Revoked status and disables actions", () => {
    const onRotate = vi.fn();
    const onRevoke = vi.fn();
    render(
      <ApiKeyList keys={[_sample[2]]} onRotate={onRotate} onRevoke={onRevoke} />,
    );
    expect(screen.getByText("Revoked")).toBeInTheDocument();
    const rotateButton = screen.getByRole("button", { name: "Rotate" });
    const revokeButton = screen.getByRole("button", { name: "Revoke" });
    expect(rotateButton).toBeDisabled();
    expect(revokeButton).toBeDisabled();
  });

  test("active key calls onRotate(keyId) when Rotate clicked", () => {
    const onRotate = vi.fn();
    render(<ApiKeyList keys={[_sample[0]]} onRotate={onRotate} />);
    fireEvent.click(screen.getByRole("button", { name: "Rotate" }));
    expect(onRotate).toHaveBeenCalledWith("key-1");
  });

  test("active key calls onRevoke(keyId) when Revoke clicked", () => {
    const onRevoke = vi.fn();
    render(<ApiKeyList keys={[_sample[0]]} onRevoke={onRevoke} />);
    fireEvent.click(screen.getByRole("button", { name: "Revoke" }));
    expect(onRevoke).toHaveBeenCalledWith("key-1");
  });
});

describe("ApiKeyRotateDialog", () => {
  test("renders 'Generating…' placeholder when plaintext=null", () => {
    render(
      <ApiKeyRotateDialog
        open
        onOpenChange={() => {}}
        plaintext={null}
        label="production"
      />,
    );
    expect(screen.getByTestId("api-key-rotate-pending")).toBeInTheDocument();
  });

  test("renders plaintext in pre block when supplied", () => {
    render(
      <ApiKeyRotateDialog
        open
        onOpenChange={() => {}}
        plaintext="sk-live-ABCDEF1234567890"
        label="production"
      />,
    );
    const pre = screen.getByTestId("api-key-rotate-plaintext");
    expect(pre).toHaveTextContent("sk-live-ABCDEF1234567890");
  });

  test("'I've saved it' button calls onAcknowledge + closes dialog", () => {
    const onAcknowledge = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <ApiKeyRotateDialog
        open
        onOpenChange={onOpenChange}
        plaintext="sk-live-ABC"
        label="production"
        onAcknowledge={onAcknowledge}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /saved it/i }));
    expect(onAcknowledge).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  test("Copy button is disabled when plaintext is null", () => {
    render(
      <ApiKeyRotateDialog
        open
        onOpenChange={() => {}}
        plaintext={null}
        label="production"
      />,
    );
    expect(
      screen.getByRole("button", { name: /copy to clipboard/i }),
    ).toBeDisabled();
  });
});
