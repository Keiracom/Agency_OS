/**
 * FILE: frontend/components/billing/StripeCheckoutButton.tsx
 * PURPOSE: Stripe Checkout button for $500 AUD founding member deposit
 * STEP: 8/8 Build Sequence
 */

"use client";

import { useState } from "react";
import { CreditCard, Loader2, Sparkles } from "lucide-react";

interface StripeCheckoutButtonProps {
  agencyId: string;
  email: string;
  agencyName: string;
  className?: string;
  variant?: "primary" | "secondary";
  disabled?: boolean;
}

export function StripeCheckoutButton({
  agencyId,
  email,
  agencyName,
  className = "",
  variant = "primary",
  disabled = false,
}: StripeCheckoutButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCheckout = async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      
      const response = await fetch(`${apiUrl}/billing/create-checkout-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          agency_id: agencyId,
          email: email,
          agency_name: agencyName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to create checkout session");
      }

      const data = await response.json();
      
      // Redirect to Stripe Checkout
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (err) {
      console.error("Checkout error:", err);
      setError(err instanceof Error ? err.message : "An error occurred");
      setLoading(false);
    }
  };

  const baseStyles = "inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-semibold text-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variantStyles = {
    primary: "bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white shadow-lg shadow-amber-500/25 hover:shadow-xl hover:shadow-amber-500/30 hover:-translate-y-0.5",
    secondary: "bg-white border-2 border-amber-500 text-amber-600 hover:bg-amber-50",
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={handleCheckout}
        disabled={disabled || loading}
        className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Redirecting to payment...</span>
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            <span>Claim Your Founding Spot — $500 AUD</span>
            <CreditCard className="w-5 h-5" />
          </>
        )}
      </button>
      
      {error && (
        <p className="text-red-500 text-sm mt-2">{error}</p>
      )}
      
      <p className="text-sm text-gray-500 mt-1">
        Refundable deposit • Credited to first month
      </p>
    </div>
  );
}

/**
 * Simplified button for landing page hero section
 */
export function FoundingDepositButton({
  className = "",
  spotsRemaining,
}: {
  className?: string;
  spotsRemaining?: number;
}) {
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [agencyName, setAgencyName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      
      // Generate a temporary agency ID for new signups
      const tempAgencyId = crypto.randomUUID();
      
      const response = await fetch(`${apiUrl}/billing/create-checkout-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          agency_id: tempAgencyId,
          email: email,
          agency_name: agencyName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to create checkout session");
      }

      const data = await response.json();
      
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (err) {
      console.error("Checkout error:", err);
      setError(err instanceof Error ? err.message : "An error occurred");
      setLoading(false);
    }
  };

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        disabled={spotsRemaining !== undefined && spotsRemaining <= 0}
        className={`inline-flex items-center justify-center gap-3 px-10 py-5 rounded-2xl font-bold text-xl 
          bg-gradient-to-r from-amber-500 via-amber-500 to-orange-500 
          hover:from-amber-600 hover:via-amber-600 hover:to-orange-600 
          text-white shadow-2xl shadow-amber-500/30 
          hover:shadow-3xl hover:shadow-amber-500/40 
          hover:-translate-y-1 
          transition-all duration-300 
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}`}
      >
        <Sparkles className="w-6 h-6" />
        <span>Secure Your Founding Spot</span>
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={`flex flex-col gap-4 max-w-md mx-auto ${className}`}>
      <div className="flex flex-col gap-3">
        <input
          type="text"
          placeholder="Agency Name"
          value={agencyName}
          onChange={(e) => setAgencyName(e.target.value)}
          required
          className="px-4 py-3 rounded-xl border border-gray-300 focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition-all"
        />
        <input
          type="email"
          placeholder="Your Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="px-4 py-3 rounded-xl border border-gray-300 focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition-all"
        />
      </div>
      
      <button
        type="submit"
        disabled={loading || !email || !agencyName}
        className="inline-flex items-center justify-center gap-3 px-8 py-4 rounded-xl font-bold text-lg 
          bg-gradient-to-r from-amber-500 to-orange-500 
          hover:from-amber-600 hover:to-orange-600 
          text-white shadow-lg shadow-amber-500/25 
          hover:shadow-xl hover:shadow-amber-500/30 
          transition-all duration-200 
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Redirecting to Stripe...</span>
          </>
        ) : (
          <>
            <CreditCard className="w-5 h-5" />
            <span>Pay $500 AUD Deposit</span>
          </>
        )}
      </button>
      
      {error && (
        <p className="text-red-500 text-sm text-center">{error}</p>
      )}
      
      <p className="text-sm text-gray-500 text-center">
        Refundable • Credited to your first month • 50% lifetime discount locked in
      </p>
      
      <button
        type="button"
        onClick={() => setShowForm(false)}
        className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
      >
        ← Back
      </button>
    </form>
  );
}
