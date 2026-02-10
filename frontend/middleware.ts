/**
 * FILE: frontend/middleware.ts
 * PURPOSE: Next.js middleware for route protection
 * MIGRATION: Updated to use @supabase/ssr (replaces auth-helpers-nextjs)
 * NOTE: Root "/" is public (landing page), dashboard requires auth
 */

import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that require authentication
// NOTE: /dashboard temporarily removed for visual review (PR #25) - will restore before merge
const protectedRoutes = ["/admin", "/onboarding", "/prototype"];

// Routes that are always public
// NOTE: /dashboard temporarily public for visual review (PR #25) - will revert before merge to main
const publicRoutes = ["/", "/login", "/signup", "/about", "/pricing", "/how-it-works", "/api", "/dashboard-v2", "/showroom", "/gallery", "/dashboard"];

export async function middleware(req: NextRequest) {
  const pathname = req.nextUrl.pathname;
  const hostname = req.headers.get("host") || "";

  // Skip auth on ALL Vercel preview/staging deployments (no custom domain yet)
  // This allows visual review without login - all data is mock anyway
  if (hostname.includes("vercel.app")) {
    return NextResponse.next();
  }

  // Always allow public routes without any redirect
  if (publicRoutes.some(route => pathname === route || pathname.startsWith(route + "/"))) {
    return NextResponse.next();
  }

  // Check auth for protected routes
  if (protectedRoutes.some(route => pathname.startsWith(route))) {
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
            cookiesToSet.forEach(({ name, value }) => req.cookies.set(name, value));
            supabaseResponse = NextResponse.next({ request: req });
            cookiesToSet.forEach(({ name, value, options }) =>
              supabaseResponse.cookies.set(name, value, options)
            );
          },
        },
      }
    );

    // Refresh session if expired
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      const loginUrl = new URL("/login", req.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }

    return supabaseResponse;
  }

  return NextResponse.next();
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
