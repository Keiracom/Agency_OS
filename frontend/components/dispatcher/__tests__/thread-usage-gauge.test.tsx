/**
 * Tests for ThreadUsageGauge component shell (KEI-161).
 *
 * Render-path-only — sub-KEI claimer extends with realtime + tier-ceiling
 * lookup tests once useThreadUsage is implemented.
 */

import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";

import { ThreadUsageGauge, type ThreadUsage } from "../thread-usage-gauge";

const _half: ThreadUsage = { active: 5, ceiling: 10, tier: "starter" };
const _atCeiling: ThreadUsage = { active: 10, ceiling: 10, tier: "growth" };
const _enterprise: ThreadUsage = { active: 1, ceiling: 1000, tier: "enterprise" };

describe("ThreadUsageGauge", () => {
  test("renders loading-state when loading=true", () => {
    render(<ThreadUsageGauge usage={null} loading />);
    expect(screen.getByTestId("thread-usage-loading")).toBeInTheDocument();
  });

  test("renders custom loadingLabel override", () => {
    render(<ThreadUsageGauge usage={null} loading loadingLabel="fetching…" />);
    expect(screen.getByText("fetching…")).toBeInTheDocument();
  });

  test("renders empty-state when usage is null and not loading", () => {
    render(<ThreadUsageGauge usage={null} />);
    expect(screen.getByTestId("thread-usage-empty")).toBeInTheDocument();
  });

  test("renders active / ceiling text + tier label when usage populated", () => {
    render(<ThreadUsageGauge usage={_half} />);
    expect(screen.getByTestId("thread-usage-gauge")).toBeInTheDocument();
    expect(screen.getByText("5 / 10 threads")).toBeInTheDocument();
    expect(screen.getByText("Starter")).toBeInTheDocument();
  });

  test("sets data-tier attribute to the usage.tier value", () => {
    render(<ThreadUsageGauge usage={_enterprise} />);
    const gauge = screen.getByTestId("thread-usage-gauge");
    expect(gauge.getAttribute("data-tier")).toBe("enterprise");
  });

  test("shows at-ceiling banner when active >= ceiling", () => {
    render(<ThreadUsageGauge usage={_atCeiling} />);
    expect(screen.getByTestId("thread-usage-at-ceiling")).toBeInTheDocument();
    expect(screen.getByTestId("thread-usage-gauge").getAttribute("data-at-ceiling")).toBe("true");
  });

  test("hides at-ceiling banner when below ceiling", () => {
    render(<ThreadUsageGauge usage={_half} />);
    expect(screen.queryByTestId("thread-usage-at-ceiling")).toBeNull();
    expect(screen.getByTestId("thread-usage-gauge").getAttribute("data-at-ceiling")).toBe("false");
  });

  test("renders Progress bar element via data-testid pass-through", () => {
    render(<ThreadUsageGauge usage={_half} />);
    expect(screen.getByTestId("thread-usage-bar")).toBeInTheDocument();
  });

  test("ceiling=0 edge case renders without divide-by-zero (pct clamps to 0)", () => {
    const broken: ThreadUsage = { active: 0, ceiling: 0, tier: "free" };
    render(<ThreadUsageGauge usage={broken} />);
    // active 0 >= ceiling 0 — at-ceiling banner shows
    expect(screen.getByTestId("thread-usage-at-ceiling")).toBeInTheDocument();
  });

  test("active > ceiling (burst race) clamps display to ceiling-equivalent banner", () => {
    const burst: ThreadUsage = { active: 15, ceiling: 10, tier: "scale" };
    render(<ThreadUsageGauge usage={burst} />);
    expect(screen.getByText("15 / 10 threads")).toBeInTheDocument();
    expect(screen.getByTestId("thread-usage-at-ceiling")).toBeInTheDocument();
  });
});
