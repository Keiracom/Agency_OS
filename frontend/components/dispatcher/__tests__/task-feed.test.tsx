/**
 * Tests for TaskFeed + TaskFeedPagination component shells.
 *
 * Render-path-only — sub-KEI claimer extends with realtime + cursor tests
 * once useTaskFeed is implemented.
 */

import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";

import { TaskFeed, type DispatcherTask } from "../task-feed";
import { TaskFeedPagination } from "../task-feed-pagination";

const _sample: DispatcherTask[] = [
  {
    id: "task-1",
    title: "First customer task",
    status: "done",
    cost_usd: 0.12,
    created_at: "2026-05-17T10:00:00Z",
    completed_at: "2026-05-17T10:05:00Z",
  },
  {
    id: "task-2",
    title: "Second task running",
    status: "active",
    cost_usd: null,
    created_at: "2026-05-17T10:30:00Z",
    completed_at: null,
  },
];

describe("TaskFeed", () => {
  test("renders empty-state message when tasks=[]", () => {
    render(<TaskFeed tasks={[]} />);
    expect(screen.getByTestId("task-feed-empty")).toBeInTheDocument();
  });

  test("renders loading-state when loading=true", () => {
    render(<TaskFeed tasks={[]} loading />);
    expect(screen.getByTestId("task-feed-loading")).toBeInTheDocument();
  });

  test("renders one row per task when populated", () => {
    render(<TaskFeed tasks={_sample} />);
    expect(screen.getByTestId("task-feed-table")).toBeInTheDocument();
    expect(screen.getByText("First customer task")).toBeInTheDocument();
    expect(screen.getByText("Second task running")).toBeInTheDocument();
  });

  test("renders dash for null cost and dollar for present cost", () => {
    render(<TaskFeed tasks={_sample} />);
    expect(screen.getByText("$0.12")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  test("custom empty message overrides default", () => {
    render(<TaskFeed tasks={[]} emptyMessage="custom empty text" />);
    expect(screen.getByText("custom empty text")).toBeInTheDocument();
  });
});

describe("TaskFeedPagination", () => {
  test("both buttons disabled when no prev and no next", () => {
    render(<TaskFeedPagination hasPrev={false} hasNext={false} />);
    expect(screen.getByText(/Previous/)).toBeDisabled();
    expect(screen.getByText(/Next/)).toBeDisabled();
  });

  test("next enabled when hasNext=true", () => {
    render(<TaskFeedPagination hasPrev={false} hasNext />);
    expect(screen.getByText(/Next/)).toBeEnabled();
  });

  test("prev enabled when hasPrev=true", () => {
    render(<TaskFeedPagination hasPrev hasNext={false} />);
    expect(screen.getByText(/Previous/)).toBeEnabled();
  });

  test("renders page label when provided", () => {
    render(<TaskFeedPagination hasPrev hasNext pageLabel="Page 2 of 5" />);
    expect(screen.getByText("Page 2 of 5")).toBeInTheDocument();
  });
});
