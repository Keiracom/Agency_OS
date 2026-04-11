/**
 * FILE: frontend/middleware.ts
 * PURPOSE: Next.js middleware for route protection + demo mode
 * MIGRATION: Updated to use @supabase/ssr (replaces auth-helpers-nextjs)
 *
 * CEO Directive #028 — Public Demo Dashboard
 * - Detect ?demo=true query parameter
 * - Bypass auth for demo mode
 * - Persist demo flag via cookies
 *
 * Directive #309 — Auth re-enabled
 * - Protected routes: /dashboard/*, /onboarding/*, /settings/*, /inbox/*,
 *   /pipeline/*, /cycles/*, /reports/*, /sequences/*
 * - Public routes: /, /login, /signup, /demo, /api/*, marketing pages
 */

import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const DEMO_COOKIE_NAME = "agency_os_demo";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/onboarding",
  "/settings",
  "/inbox",
  "/pipeline",
  "/cycles",
  "/reports",
  "/sequences",
];

const PUBLIC_PREFIXES = [
  "/",
  "/login",
  "/signup",
  "/demo",
  "/api",
  "/about",
  "/pricing",
  "/how-it-works",
  "/privacy",
  "/showroom",
  "/gallery",
];

function isPublicRoute(pathname: string): boolean {
  // Exact match on "/" or prefix match on everything else
  if (pathname === "/") return true;
  return PUBLIC_PREFIXES.slice(1).some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix + "/")
  );
}

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix + "/")
  );
}

export async function middleware(req: NextRequest) {
  const { pathname, searchParams } = req.nextUrl;

  // ---- Demo mode handling ----
  const demoParam = searchParams.get("demo");
  const demoCookie = req.cookies.get(DEMO_COOKIE_NAME)?.value;
  let isDemo = false;

  let baseResponse = NextResponse.next({ request: req });

  if (demoParam === "true") {
    isDemo = true;
    baseResponse.cookies.set(DEMO_COOKIE_NAME, "true", {
      httpOnly: false,
      sameSite: "lax",
      maxAge: 60 * 60 * 24,
      path: "/",
    });
  } else if (demoParam === "false") {
    isDemo = false;
    baseResponse.cookies.delete(DEMO_COOKIE_NAME);
  } else if (demoCookie === "true") {
    isDemo = true;
  }

  // Demo mode bypasses all auth
  if (isDemo) {
    baseResponse.headers.set("x-demo-mode", "true");
    return baseResponse;
  }

  // ---- Auth gate for protected routes ----
  if (!isProtectedRoute(pathname) || isPublicRoute(pathname)) {
    return baseResponse;
  }

  let supabaseResponse = NextResponse.next({ request: req });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return req.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            req.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request: req });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("returnTo", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
