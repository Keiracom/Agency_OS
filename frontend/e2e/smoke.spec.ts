import { expect, test } from "@playwright/test";

// SMOKE — auth gate + dashboard render verification
//
// Closes V6 UNVERIFIED items from Aiden audit_verify 2026-05-08:
//   - "Signup form actually renders and submits (CSR, no browser test)"
//   - "Dashboard renders meaningful content post-login (no test account)"
//
// HOLD-FIRE: this spec MUST NOT run against production until Phase 0
// authorizes test-account creation. Use the demo-tenant seeded by
// scripts/seed_demo_tenant.py for stable test identity.
//
// Pre-flight before running:
//   1. Phase 0 trigger lands (Salesforge + Unipile keys regenerated)
//   2. seed_demo_tenant.py wired to provide TEST_LOGIN_EMAIL +
//      TEST_LOGIN_PASSWORD env vars (or local .env.test)
//   3. PLAYWRIGHT_BASE_URL set if targeting non-prod
//
// Run mode:
//   npx playwright test e2e/smoke.spec.ts --project=chromium
//
// Status: SCAFFOLD — config + spec authored 2026-05-08, hold-fire on
// run pending Phase 0 trigger + test-account provisioning.

test.describe("Agency OS frontend smoke", () => {
  test("public landing renders with title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Agency OS/i);
  });

  test("auth gate redirects unauthed /dashboard to /login", async ({ page }) => {
    const response = await page.goto("/dashboard");
    expect(response?.status()).toBe(200);
    await expect(page).toHaveURL(/\/login/);
  });

  test("signup page renders form inputs", async ({ page }) => {
    await page.goto("/signup");
    await expect(page).toHaveTitle(/Agency OS/i);
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 10000 });
  });

  test.skip("authed dashboard renders content", async ({ page }) => {
    // HOLD-FIRE — requires seeded test account from seed_demo_tenant.py.
    // Unskip only after Phase 0 lands AND TEST_LOGIN_* env vars exist.
    const email = process.env.TEST_LOGIN_EMAIL;
    const password = process.env.TEST_LOGIN_PASSWORD;
    if (!email || !password) {
      test.skip(true, "TEST_LOGIN_* env vars required");
    }
    await page.goto("/login");
    await page.fill('input[type="email"]', email!);
    await page.fill('input[type="password"]', password!);
    await page.click('button[type="submit"]');
    await page.waitForURL("**/dashboard");
    await expect(page.locator("main")).not.toBeEmpty();
  });
});
