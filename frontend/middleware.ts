/**
 * FILE: frontend/middleware.ts
 * PURPOSE: Next.js middleware for route protection
 * NOTE: Root "/" is public (landing page), dashboard requires auth
 */

import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that require authentication
const protectedRoutes = ["/dashboard", "/admin", "/onboarding", "/prototype"];

// Routes that are always public
const publicRoutes = ["/", "/login", "/signup", "/about", "/pricing", "/how-it-works", "/api", "/dashboard-v2", "/showroom", "/gallery"];

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const pathname = req.nextUrl.pathname;

  // Always allow public routes without any redirect
  if (publicRoutes.some(route => pathname === route || pathname.startsWith(route + "/"))) {
    return res;
  }

  // Check auth for protected routes
  if (protectedRoutes.some(route => pathname.startsWith(route))) {
    const supabase = createMiddlewareClient({ req, res });
    const { data: { session } } = await supabase.auth.getSession();

    if (!session) {
      const loginUrl = new URL("/login", req.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return res;
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
