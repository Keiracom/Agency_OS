/**
 * Tests for FirstTaskForm component shell (KEI-156).
 *
 * Interaction-heavy — covers validation, submit success, submit failure,
 * pending state lockout. Sub-KEI extends with end-to-end Prefect enqueue
 * confirmation tests once useFirstTaskSubmit is implemented.
 */

import { describe, expect, test, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { FirstTaskForm } from "../first-task-form";

function _setup(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  render(<FirstTaskForm onSubmit={onSubmit} />);
  const title = screen.getByTestId("first-task-title-input") as HTMLInputElement;
  const desc = screen.getByTestId("first-task-description-input") as HTMLTextAreaElement;
  const submit = screen.getByTestId("first-task-submit") as HTMLButtonElement;
  return { onSubmit, title, desc, submit };
}

describe("FirstTaskForm", () => {
  test("renders form heading, inputs, submit button", () => {
    _setup();
    expect(screen.getByTestId("first-task-form")).toBeInTheDocument();
    expect(screen.getByText("Submit your first task")).toBeInTheDocument();
    expect(screen.getByTestId("first-task-title-input")).toBeInTheDocument();
    expect(screen.getByTestId("first-task-description-input")).toBeInTheDocument();
    expect(screen.getByTestId("first-task-submit")).toBeInTheDocument();
  });

  test("custom heading prop overrides default", () => {
    render(<FirstTaskForm onSubmit={vi.fn()} heading="Onboarding step 3" />);
    expect(screen.getByText("Onboarding step 3")).toBeInTheDocument();
  });

  test("rejects title shorter than 4 chars with inline error", async () => {
    const { onSubmit, title, submit } = _setup();
    fireEvent.change(title, { target: { value: "hi" } });
    fireEvent.click(submit);
    await waitFor(() => {
      expect(screen.getByTestId("first-task-error")).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("rejects empty title with inline error", async () => {
    const { onSubmit, submit } = _setup();
    fireEvent.click(submit);
    await waitFor(() => {
      expect(screen.getByTestId("first-task-error")).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("calls onSubmit with trimmed title + raw description when valid", async () => {
    const { onSubmit, title, desc, submit } = _setup();
    fireEvent.change(title, { target: { value: "  hello world  " } });
    fireEvent.change(desc, { target: { value: "some details" } });
    fireEvent.click(submit);
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      title: "hello world",
      description: "some details",
    });
  });

  test("switches to pending state on success + locks form + shows pendingLabel", async () => {
    const { onSubmit, title, submit } = _setup();
    fireEvent.change(title, { target: { value: "valid task" } });
    fireEvent.click(submit);
    await waitFor(() => {
      expect(screen.getByTestId("first-task-pending")).toBeInTheDocument();
    });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const form = screen.getByTestId("first-task-form");
    expect((form as HTMLElement).dataset.state).toBe("pending");
  });

  test("custom pendingLabel prop overrides default", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<FirstTaskForm onSubmit={onSubmit} pendingLabel="hang tight" />);
    fireEvent.change(screen.getByTestId("first-task-title-input"), {
      target: { value: "valid task" },
    });
    fireEvent.click(screen.getByTestId("first-task-submit"));
    await waitFor(() => {
      expect(screen.getByText("hang tight")).toBeInTheDocument();
    });
  });

  test("switches to error state when onSubmit rejects", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("network down"));
    render(<FirstTaskForm onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("first-task-title-input"), {
      target: { value: "valid task" },
    });
    fireEvent.click(screen.getByTestId("first-task-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("first-task-error")).toBeInTheDocument();
    });
    expect(screen.getByText("network down")).toBeInTheDocument();
  });

  test("non-Error thrown value surfaces generic error message", async () => {
    const onSubmit = vi.fn().mockRejectedValue("string-not-error");
    render(<FirstTaskForm onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("first-task-title-input"), {
      target: { value: "valid task" },
    });
    fireEvent.click(screen.getByTestId("first-task-submit"));
    await waitFor(() => {
      expect(screen.getByText("Submission failed.")).toBeInTheDocument();
    });
  });

  test("data-state attribute reflects current state machine", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<FirstTaskForm onSubmit={onSubmit} />);
    const form = screen.getByTestId("first-task-form");
    expect((form as HTMLElement).dataset.state).toBe("idle");
    fireEvent.change(screen.getByTestId("first-task-title-input"), {
      target: { value: "valid task" },
    });
    fireEvent.click(screen.getByTestId("first-task-submit"));
    await waitFor(() => {
      expect((form as HTMLElement).dataset.state).toBe("pending");
    });
  });
});
