"use client";

/**
 * FILE: frontend/app/(auth)/signup/page.tsx
 * PURPOSE: Signup form — cream/amber /demo palette. Playfair
 *          headline, JetBrains Mono labels, DM Sans body.
 * UPDATED: 2026-04-30 — A6 auth refinement.
 *
 * Auth logic (Supabase signUp + email confirmation flow) is
 * unchanged; only chrome was repalleted.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createBrowserClient } from "../../../lib/supabase";
import { useToast } from "../../../hooks/use-toast";
import { Loader2 } from "lucide-react";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const supabase = createBrowserClient();
  const { toast } = useToast();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName, company_name: companyName },
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });
      if (error) {
        toast({ title: "Signup failed", description: error.message, variant: "destructive" });
        return;
      }
      if (data.user) {
        toast({
          title: "Check your email",
          description: "We sent you a confirmation link to complete your signup.",
        });
        router.push("/login");
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
        Create your <em className="text-amber" style={{ fontStyle: "italic" }}>account</em>
      </h1>
      <p className="text-[13px] text-ink-3 mt-1.5 mb-6">
        Join AgencyOS — 16+ meetings guaranteed or your money back.
      </p>

      <form onSubmit={handleSignup} className="space-y-4">
        <Field
          id="fullName"
          label="Full name"
          type="text"
          placeholder="John Smith"
          value={fullName}
          onChange={setFullName}
          autoComplete="name"
          loading={loading}
        />
        <Field
          id="companyName"
          label="Agency name"
          type="text"
          placeholder="Acme Agency"
          value={companyName}
          onChange={setCompanyName}
          autoComplete="organization"
          loading={loading}
        />
        <Field
          id="email"
          label="Email"
          type="email"
          placeholder="you@agency.com"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          loading={loading}
        />
        <Field
          id="password"
          label="Password"
          type="password"
          placeholder="Create a password (min 8 chars)"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          minLength={8}
          loading={loading}
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-[8px] bg-ink text-white font-mono text-[12px] tracking-[0.08em] uppercase font-semibold py-3 hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Creating account…
            </>
          ) : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-center text-[11.5px] text-ink-3 leading-relaxed">
        By signing up, you agree to our{" "}
        <Link href="/terms" className="text-copper hover:text-amber transition-colors">Terms</Link>{" "}
        and{" "}
        <Link href="/privacy" className="text-copper hover:text-amber transition-colors">Privacy Policy</Link>.
      </p>

      <p className="mt-4 text-center text-[13px] text-ink-3">
        Already have an account?{" "}
        <Link href="/login" className="text-copper hover:text-amber transition-colors font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}

function Field({
  id, label, type, placeholder, value, onChange, autoComplete, minLength, loading,
}: {
  id: string;
  label: string;
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  minLength?: number;
  loading?: boolean;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 mb-1.5"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        minLength={minLength}
        disabled={loading}
        className="w-full rounded-[8px] border border-rule bg-cream px-3 py-2.5 text-[14px] text-ink placeholder:text-ink-4 font-mono focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 transition-colors disabled:opacity-60"
      />
    </div>
  );
}
