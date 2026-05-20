/**
 * FILE: frontend/components/dispatcher/first-task-form.tsx
 * PURPOSE: Form for the customer's first dispatched task. Onboarding step
 *          that lands them at their dashboard with a task in-flight.
 * KEI: 156 (Part 17.3 sub-KEI — first-task submission).
 *
 * Render-path complete: typed form + client-side validation + submit
 * callback contract. Sub-KEI claimer wires the backend `submitTask`
 * function to INSERT into public.tasks + trigger the Prefect flow.
 *
 * Title/description trimmed pre-submit. Empty title rejects with inline
 * error. Disable submit while in-flight + on the pending state.
 */

"use client";

import * as React from "react";

export interface FirstTaskFormValues {
  title: string;
  description: string;
}

export type FirstTaskSubmitState = "idle" | "submitting" | "pending" | "error";

export interface FirstTaskFormProps {
  /** Async hook to actually create the task. Returns nothing on success;
   *  throws on failure. Sub-KEI implementation: INSERT public.tasks +
   *  Prefect enqueue. */
  onSubmit: (values: FirstTaskFormValues) => Promise<void>;
  /** Visible after submission succeeds — sub-KEI dashboard-populate hook
   *  uses this to wait for the first task to complete then redirect. */
  pendingLabel?: string;
  /** Override for the form heading (kept for the page.tsx wrapper). */
  heading?: string;
}

const MAX_TITLE_LEN = 200;
const MAX_DESC_LEN = 2000;
const MIN_TITLE_LEN = 4;

function _validate(values: FirstTaskFormValues): string | null {
  const title = values.title.trim();
  if (title.length < MIN_TITLE_LEN) {
    return `Title must be at least ${MIN_TITLE_LEN} characters.`;
  }
  if (title.length > MAX_TITLE_LEN) {
    return `Title must be ${MAX_TITLE_LEN} characters or fewer.`;
  }
  if (values.description.length > MAX_DESC_LEN) {
    return `Description must be ${MAX_DESC_LEN} characters or fewer.`;
  }
  return null;
}

export function FirstTaskForm({
  onSubmit,
  pendingLabel = "Task submitted — preparing your dashboard…",
  heading = "Submit your first task",
}: Readonly<FirstTaskFormProps>) {
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [state, setState] = React.useState<FirstTaskSubmitState>("idle");
  const [error, setError] = React.useState<string | null>(null);

  const disabled = state === "submitting" || state === "pending";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const values: FirstTaskFormValues = { title: title.trim(), description };
    const validationError = _validate(values);
    if (validationError) {
      setError(validationError);
      setState("error");
      return;
    }
    setError(null);
    setState("submitting");
    try {
      await onSubmit(values);
      setState("pending");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
      setState("error");
    }
  };

  return (
    <form
      data-testid="first-task-form"
      data-state={state}
      onSubmit={handleSubmit}
      className="mx-auto max-w-md space-y-4 p-8"
    >
      <h1 className="text-2xl font-semibold">{heading}</h1>
      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="first-task-title">
          Title
        </label>
        <input
          id="first-task-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={MAX_TITLE_LEN}
          disabled={disabled}
          required
          className="w-full rounded border px-3 py-2 text-sm"
          data-testid="first-task-title-input"
        />
      </div>
      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="first-task-description">
          Description (optional)
        </label>
        <textarea
          id="first-task-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={MAX_DESC_LEN}
          disabled={disabled}
          rows={6}
          className="w-full rounded border px-3 py-2 text-sm"
          data-testid="first-task-description-input"
        />
      </div>
      {error ? (
        <p data-testid="first-task-error" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {state === "pending" ? (
        <p data-testid="first-task-pending" className="text-sm text-muted-foreground">
          {pendingLabel}
        </p>
      ) : (
        <button
          type="submit"
          disabled={disabled}
          className="rounded border px-4 py-2 text-sm font-medium disabled:opacity-50"
          data-testid="first-task-submit"
        >
          {state === "submitting" ? "Submitting…" : "Submit task"}
        </button>
      )}
    </form>
  );
}
