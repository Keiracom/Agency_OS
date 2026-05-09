/**
 * Tests for the 3 dashboard API routes wired in A2 (PR #639).
 * Covers auth gate + happy path + empty state for each route.
 *
 * Mocks @/lib/supabase/server's createClient to avoid hitting real Supabase
 * or needing cookies/next-headers infrastructure.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

type MockChain = {
  data: unknown;
  error: unknown;
  authedUser: unknown;
};

const buildMockClient = (chain: MockChain) => {
  const builder: Record<string, unknown> = {};
  const fn = () => builder;
  builder.select = fn;
  builder.eq = fn;
  builder.in = fn;
  builder.lt = fn;
  builder.order = fn;
  builder.limit = vi.fn(() =>
    Promise.resolve({ data: chain.data, error: chain.error })
  );
  // For leads/counts: terminal `.select(...)` returns the promise directly.
  // Re-assign select to return a thenable when called as terminal op.
  builder.select = vi.fn(() => {
    const obj: Record<string, unknown> = { ...builder };
    (obj as { then: (cb: (v: unknown) => unknown) => Promise<unknown> }).then = (
      cb,
    ) =>
      Promise.resolve({ data: chain.data, error: chain.error }).then(cb);
    return obj;
  });

  return {
    from: vi.fn(() => builder),
    auth: {
      getUser: vi.fn(() =>
        Promise.resolve({ data: { user: chain.authedUser }, error: null }),
      ),
    },
  };
};

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

import { createClient } from "@/lib/supabase/server";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("/api/activity", () => {
  it("returns 401 when no authenticated user", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({ data: [], error: null, authedUser: null }),
    );
    const { GET } = await import("../activity/route");
    const res = await GET(new NextRequest("http://x/api/activity"));
    expect(res.status).toBe(401);
  });

  it("returns honest empty array when no rows", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({ data: [], error: null, authedUser: { id: "u1" } }),
    );
    const { GET } = await import("../activity/route");
    const res = await GET(new NextRequest("http://x/api/activity"));
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(json.data).toEqual([]);
    expect(json.hasMore).toBe(false);
  });
});

describe("/api/replies", () => {
  it("returns 401 when no authenticated user", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({ data: [], error: null, authedUser: null }),
    );
    const { GET } = await import("../replies/route");
    const res = await GET(new NextRequest("http://x/api/replies"));
    expect(res.status).toBe(401);
  });

  it("returns empty replies + zero unread when no rows", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({ data: [], error: null, authedUser: { id: "u1" } }),
    );
    const { GET } = await import("../replies/route");
    const res = await GET(new NextRequest("http://x/api/replies"));
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(json.data).toEqual([]);
    expect(json.total).toBe(0);
    expect(json.unread).toBe(0);
  });
});

describe("/api/leads/counts", () => {
  it("returns 401 when no authenticated user", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({ data: [], error: null, authedUser: null }),
    );
    const { GET } = await import("../leads/counts/route");
    const res = await GET();
    expect(res.status).toBe(401);
  });

  it("aggregates als_tier values correctly with zero total", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({ data: [], error: null, authedUser: { id: "u1" } }),
    );
    const { GET } = await import("../leads/counts/route");
    const res = await GET();
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(json.total).toBe(0);
    expect(json.data).toHaveLength(5);
    expect(json.data.map((t: { tier: string }) => t.tier)).toEqual([
      "hot",
      "warm",
      "cool",
      "cold",
      "unscored",
    ]);
    // All percentages 0 when total = 0 (no NaN)
    for (const t of json.data) {
      expect(t.percentage).toBe(0);
      expect(t.count).toBe(0);
    }
  });

  it("aggregates als_tier values correctly with mixed rows", async () => {
    (createClient as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue(
      buildMockClient({
        data: [
          { als_tier: "hot" },
          { als_tier: "hot" },
          { als_tier: "cold" },
          { als_tier: null },
          { als_tier: "garbage_value" }, // unknown -> bucketed to unscored
        ],
        error: null,
        authedUser: { id: "u1" },
      }),
    );
    const { GET } = await import("../leads/counts/route");
    const res = await GET();
    const json = await res.json();
    expect(json.total).toBe(5);
    const byTier = Object.fromEntries(
      json.data.map((t: { tier: string; count: number }) => [t.tier, t.count]),
    );
    expect(byTier.hot).toBe(2);
    expect(byTier.cold).toBe(1);
    expect(byTier.unscored).toBe(2); // null + garbage_value
  });
});
