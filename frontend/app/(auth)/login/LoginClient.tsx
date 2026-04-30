/**
 * FILE: app/(auth)/login/LoginClient.tsx
 * PURPOSE: Sign-in form — cream/amber /demo palette. Playfair
 *          headline, JetBrains Mono labels, DM Sans body.
 * UPDATED: 2026-04-30 — A6 auth refinement.
 *
 * Auth logic (Supabase calls, redirect, toast on error) is
 * unchanged from the pre-A6 implementation; only chrome was
 * repalleted.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createBrowserClient } from "../../../lib/supabase";
import { useToast } from "../../../hooks/use-toast";
import { Loader2 } from "lucide-react";

export default function LoginClient() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const supabase = createBrowserClient();
  const { toast } = useToast();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        toast({
          title: "Login failed",
          description: error.message,
          variant: "destructive",
        });
        return;
      }

      if (data.user) {
        toast({
          title: "Welcome back",
          description: "Redirecting to dashboard…",
        });
        router.push("/dashboard");
        router.refresh();
      }
    } catch {
      toast({
        title: "Error",
        description: "An unexpected error occurred. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/auth/callback` },
      });
      if (error) {
        toast({
          title: "Login failed",
          description: error.message,
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Error",
        description: "An unexpected error occurred. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full rounded-[12px] border border-rule bg-panel px-7 py-8 shadow-[0_1px_2px_rgba(12,10,8,0.04)]">
      <h1 className="font-display font-bold text-[28px] leading-[1.2] tracking-[-0.02em] text-ink">
        Welcome <em className="text-amber" style={{ fontStyle: "italic" }}>back</em>
      </h1>
      <p className="text-[13px] text-ink-3 mt-1.5 mb-6">
        Sign in to your AgencyOS account.
      </p>

      <form onSubmit={handleLogin} className="space-y-4">
        <div>
          <label
            htmlFor="email"
            className="block font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 mb-1.5"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            placeholder="you@agency.com"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
            className="w-full rounded-[8px] border border-rule bg-cream px-3 py-2.5 text-[14px] text-ink placeholder:text-ink-4 font-mono focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 transition-colors disabled:opacity-60"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label
              htmlFor="password"
              className="block font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3"
            >
              Password
            </label>
            <Link
              href="/forgot-password"
              className="font-mono text-[10px] tracking-[0.06em] text-copper hover:text-amber transition-colors"
            >
              Forgot password?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            placeholder="Enter your password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
            className="w-full rounded-[8px] border border-rule bg-cream px-3 py-2.5 text-[14px] text-ink placeholder:text-ink-4 font-mono focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 transition-colors disabled:opacity-60"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-[8px] bg-ink text-white font-mono text-[12px] tracking-[0.08em] uppercase font-semibold py-3 hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Signing in…
            </>
          ) : "Sign in"}
        </button>
      </form>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-rule" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-panel px-3 font-mono text-[9px] tracking-[0.16em] uppercase text-ink-3">
            Or continue with
          </span>
        </div>
      </div>

      <button
        type="button"
        onClick={handleGoogleLogin}
        disabled={loading}
        className="w-full rounded-[8px] border border-rule bg-panel hover:border-amber hover:bg-amber-soft transition-colors py-3 flex items-center justify-center gap-2 text-[13px] font-medium text-ink disabled:opacity-60"
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden>
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
        </svg>
        Continue with Google
      </button>

      <p className="mt-6 text-center text-[13px] text-ink-3">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="text-copper hover:text-amber transition-colors font-medium">
          Sign up
        </Link>
      </p>
    </div>
  );
}
