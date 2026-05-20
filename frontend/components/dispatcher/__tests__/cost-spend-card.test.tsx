/**
 * FILE: frontend/components/dispatcher/__tests__/cost-spend-card.test.tsx
 * PURPOSE: Render tests for CostSpendCard — LAW II AUD compliance + states.
 * KEI: KEI-159 (KEI-114B)
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CostSpendCard } from "../cost-spend-card";

describe("CostSpendCard", () => {
  it("renders loading skeleton when loading=true", () => {
    render(<CostSpendCard totalAud={null} periodLabel="Last 30 days" loading={true} />);
    expect(screen.getByRole("status", { name: /loading spend data/i })).toBeDefined();
  });

  it("renders 'No spend yet' when totalAud is null", () => {
    render(<CostSpendCard totalAud={null} periodLabel="Last 30 days" />);
    expect(screen.getByText("No spend yet")).toBeDefined();
  });

  it("renders A$ prefix and AUD suffix when totalAud is a number", () => {
    render(<CostSpendCard totalAud={12.5} periodLabel="Last 30 days" />);
    const text = screen.getByText(/A\$12\.50 AUD/);
    expect(text).toBeDefined();
  });

  it("renders the periodLabel below the spend value", () => {
    render(<CostSpendCard totalAud={0} periodLabel="Last 30 days" />);
    expect(screen.getByText("Last 30 days")).toBeDefined();
  });

  it("renders totalAud with 2-decimal precision", () => {
    render(<CostSpendCard totalAud={1.1} periodLabel="This month" />);
    expect(screen.getByText("A$1.10 AUD")).toBeDefined();
  });

  it("renders zero spend as A$0.00 AUD, not 'No spend yet'", () => {
    render(<CostSpendCard totalAud={0} periodLabel="This month" />);
    expect(screen.getByText("A$0.00 AUD")).toBeDefined();
  });
});
