/**
 * Tests for FirstTaskSuccessBanner.
 * KEI: 157 — KEI-113D dashboard populate on first-task completion.
 */

import { describe, expect, test, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  FirstTaskSuccessBanner,
} from "../first-task-success-banner";
import type { DispatcherTask } from "../task-feed";

const sampleTask: DispatcherTask = {
  id: "task-99",
  title: "Prospect Australian SMBs in Melbourne",
  status: "done",
  cost_aud: 1.25,
  created_at: "2026-05-17T08:00:00Z",
  completed_at: "2026-05-17T08:10:00Z",
};

describe("FirstTaskSuccessBanner", () => {
  test("returns null when task is null", () => {
    const { container } = render(
      <FirstTaskSuccessBanner task={null} visible onDismiss={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  test("returns null when visible is false", () => {
    const { container } = render(
      <FirstTaskSuccessBanner task={sampleTask} visible={false} onDismiss={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  test("renders task title when visible and task is set", () => {
    render(
      <FirstTaskSuccessBanner task={sampleTask} visible onDismiss={vi.fn()} />
    );
    expect(screen.getByTestId("banner-task-title")).toHaveTextContent(
      "Prospect Australian SMBs in Melbourne"
    );
  });

  test("renders dismiss button when visible", () => {
    render(
      <FirstTaskSuccessBanner task={sampleTask} visible onDismiss={vi.fn()} />
    );
    expect(screen.getByTestId("banner-dismiss-button")).toBeInTheDocument();
  });

  test("dismiss click invokes onDismiss callback", () => {
    const onDismiss = vi.fn();
    render(
      <FirstTaskSuccessBanner task={sampleTask} visible onDismiss={onDismiss} />
    );
    fireEvent.click(screen.getByTestId("banner-dismiss-button"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  test("banner copy contains 'first task' phrase", () => {
    render(
      <FirstTaskSuccessBanner task={sampleTask} visible onDismiss={vi.fn()} />
    );
    expect(
      screen.getByRole("status").textContent?.toLowerCase()
    ).toContain("first task");
  });

  test("banner has role='status' for accessible announcement", () => {
    render(
      <FirstTaskSuccessBanner task={sampleTask} visible onDismiss={vi.fn()} />
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
