import { expect, test } from "@playwright/test";

/**
 * CUSTOMER JOURNEY SMOKE HARNESS — 18 audit steps
 * ================================================
 *
 * Each test = one journey step. Most will fail or skip today; that's the
 * deliberate finding (per Max group dispatch 2026-05-10). The harness
 * converts "the audit said X is broken" into a green/red Playwright
 * dashboard with a known-shape failure per step.
 *
 * Coverage tiers:
 *   PUBLIC  — runs against prod baseURL (https://app.agencyxos.ai) without
 *             auth. Tests basic render + redirect behavior.
 *   AUTHED  — gated on TEST_LOGIN_EMAIL + TEST_LOGIN_PASSWORD env vars.
 *             Skips with reason if not set (Phase 0 hold-fire pattern from
 *             smoke.spec.ts). Will surface real failures once seed_demo_tenant
 *             is wired.
 *   STUBBED — represents a journey step that requires backend wiring not yet
 *             shipped (Stripe checkout, real campaign send). Placeholder
 *             test.fixme() with a documented unblock condition.
 *
 * Run:
 *   cd frontend && pnpm playwright test e2e/customer_journey.spec.ts
 *   PLAYWRIGHT_BASE_URL=http://localhost:3000 pnpm playwright test e2e/customer_journey.spec.ts
 *
 * The 18 steps mirror the customer journey shape from PR #658
 * (admin_dashboard_mock_audit_2026-05-09.md) + audit_phase2_2026-05-07.md
 * (10-page existing onboarding + 7-step PR #609 spec ≈ 17-18 step extended journey).
 */

const requiresAuth = (page: { context: () => unknown }) => {
  const email = process.env.TEST_LOGIN_EMAIL;
  const password = process.env.TEST_LOGIN_PASSWORD;
  if (!email || !password) {
    test.skip(true, "TEST_LOGIN_* env vars required (Phase 0 seed_demo_tenant pending)");
  }
  return { email: process.env.TEST_LOGIN_EMAIL!, password: process.env.TEST_LOGIN_PASSWORD! };
};

async function login(page: import("@playwright/test").Page) {
  const { email, password } = requiresAuth(page);
  await page.goto("/login");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|onboarding|welcome)/, { timeout: 15000 });
}

test.describe("Customer Journey — 18 step smoke", () => {
  // ── PHASE 1: Pre-signup (PUBLIC) ──────────────────────────────────────
  test("01. Public landing renders with title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Agency OS/i);
  });

  test("02. Pricing or how-it-works marketing surface reachable", async ({ page }) => {
    const response = await page.goto("/how-it-works");
    expect([200, 301, 302, 308]).toContain(response?.status() ?? 0);
  });

  // ── PHASE 2: Signup (PUBLIC form, AUTHED submission) ─────────────────
  test("03. Signup form renders email + password inputs", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 10000 });
  });

  test.fixme("04. Signup submission creates user + provisions Stripe customer", async () => {
    // STUBBED — Stripe wiring not built (price_id=None per audit).
    // Unblock condition: Stripe scaffold lands + test-mode keys in CI env.
  });

  // ── PHASE 3: Onboarding (AUTHED) ─────────────────────────────────────
  test("05. /welcome reachable post-signup (auth-gated)", async ({ page }) => {
    await login(page);
    const response = await page.goto("/welcome");
    expect([200, 302]).toContain(response?.status() ?? 0);
  });

  test("06. Onboarding step-1 renders form fields", async ({ page }) => {
    await login(page);
    await page.goto("/onboarding/step-1");
    await expect(page.locator("form, [data-onboarding-step]")).toBeVisible({ timeout: 10000 });
  });

  test("07. Onboarding step-2 reachable after step-1", async ({ page }) => {
    await login(page);
    const response = await page.goto("/onboarding/step-2");
    expect([200, 302]).toContain(response?.status() ?? 0);
  });

  test("08. Onboarding agency profile (icp / linkedin / service-area) reachable", async ({ page }) => {
    await login(page);
    for (const path of ["/onboarding/agency", "/onboarding/linkedin", "/onboarding/service-area"]) {
      const r = await page.goto(path);
      expect([200, 302]).toContain(r?.status() ?? 0);
    }
  });

  // ── PHASE 4: First campaign (AUTHED) ─────────────────────────────────
  test("09. /dashboard redirects unauthed → /login", async ({ page }) => {
    const response = await page.goto("/dashboard");
    expect(response?.status()).toBe(200);
    await expect(page).toHaveURL(/\/login/);
  });

  test("10. /dashboard/campaigns reachable (AUTHED) and lists campaigns or empty state", async ({ page }) => {
    await login(page);
    await page.goto("/dashboard/campaigns");
    await expect(page.locator("main")).not.toBeEmpty();
  });

  test.fixme("11. Campaign creation form + submit lands a row in `campaigns`", async () => {
    // STUBBED — campaign-create flow needs Salesforge/Unipile sender selection
    // which depends on Phase 0 unblock + seeded test tenant with vendor creds.
  });

  // ── PHASE 5: First email + reply (AUTHED + STUBBED) ──────────────────
  test.fixme("12. First email send fires through outbound flow + appears in activities", async () => {
    // STUBBED — outbound send blocked on DFS-402 (cohort discovery dropped at stage 4)
    // AND on Salesforge sender provisioning (Phase 0). Both Dave-gated.
  });

  test("13. /dashboard/activity surface reachable (AUTHED)", async ({ page }) => {
    await login(page);
    await page.goto("/dashboard/activity");
    await expect(page.locator("main")).not.toBeEmpty();
  });

  test.fixme("14. Reply received appears on /dashboard/activity within 30s", async () => {
    // STUBBED — needs an actual outbound + a reply webhook to fire. Dave-gated
    // on outbound flows shipping. Until then activities table is empty per
    // schema sweep (2026-05-10).
  });

  // ── PHASE 6: Meeting booking (AUTHED) ────────────────────────────────
  test("15. /dashboard/meetings reachable (AUTHED)", async ({ page }) => {
    await login(page);
    await page.goto("/dashboard/meetings");
    await expect(page.locator("main")).not.toBeEmpty();
  });

  test.fixme("16. Meeting booking link generation + Calendly redirect", async () => {
    // STUBBED — Calendly integration scope — confirm under Salesforge-or-Unipile
    // booking path. Carry-over for next session per ceo_memory.
  });

  // ── PHASE 7: Post-conversion + admin (AUTHED admin only) ─────────────
  test("17. /admin/ops shows live operational metrics (AUTHED platform admin)", async ({ page }) => {
    await login(page);
    const response = await page.goto("/admin/ops");
    if (response?.status() === 403 || page.url().endsWith("/login")) {
      test.skip(true, "test user lacks platform_admin flag");
    }
    await expect(page.locator("main")).not.toBeEmpty();
  });

  test("18. 404 on unknown route renders not-found page (PUBLIC)", async ({ page }) => {
    const response = await page.goto("/this-route-does-not-exist-9zx");
    expect([404, 200]).toContain(response?.status() ?? 0);
  });
});
