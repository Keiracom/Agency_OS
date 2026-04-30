"use client";

/**
 * FILE: frontend/app/welcome/page.tsx
 * PURPOSE: Post-deposit welcome page for founding members
 * DIRECTIVE: #314 — Task B
 * DESIGN: Matches prototype_welcome_page.html exactly
 *   cream #F7F3EE bg, ink #0C0A08 text, amber #D4956A accents
 *   Playfair Display headlines, DM Sans body, JetBrains Mono labels
 * STATE:
 *   - No subscription → redirect to /
 *   - Subscription, no onboarding → show welcome
 *   - Onboarding complete → redirect to /dashboard
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createBrowserClient } from "@/lib/supabase";

interface ClientData {
  name: string;
  tier: string;
  deposit_paid: boolean;
  founding_position: number | null;
  monthly_rate_aud: number | null;
}

interface OnboardingStatus {
  complete: boolean;
}

export default function WelcomePage() {
  const router = useRouter();
  const supabase = createBrowserClient();
  const [client, setClient] = useState<ClientData | null>(null);
  const [loading, setLoading] = useState(true);
  const [position, setPosition] = useState<number>(4);
  const [monthlyRate, setMonthlyRate] = useState<number>(1250);
  const [standardRate, setStandardRate] = useState<number>(2500);
  const [tier, setTier] = useState<string>("Ignition");

  useEffect(() => {
    async function checkState() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.replace("/");
        return;
      }

      // Get membership → client
      const { data: membership } = await supabase
        .from("memberships")
        .select("client_id, clients(id, name, tier, deposit_paid)")
        .eq("user_id", user.id)
        .eq("role", "owner")
        .single();

      if (!membership || !(membership as Record<string, unknown>).clients) {
        router.replace("/");
        return;
      }

      const clientRow = (membership as Record<string, unknown>).clients as {
        id: string;
        name: string;
        tier: string;
        deposit_paid: boolean;
      };

      if (!clientRow.deposit_paid) {
        router.replace("/");
        return;
      }

      // Check onboarding completion
      const { data: onboarding } = await supabase
        .from("clients")
        .select("website_url, icp_extracted")
        .eq("id", clientRow.id)
        .single();

      const ob = onboarding as Record<string, unknown> | null;
      const onboardingComplete =
        ob?.website_url && ob?.icp_extracted;

      if (onboardingComplete) {
        router.replace("/dashboard");
        return;
      }

      // Get founding position from founding_spots count
      const { data: spotsRow } = await supabase
        .from("founding_spots")
        .select("spots_taken")
        .eq("id", 1)
        .single();

      const pos = (spotsRow as Record<string, unknown> | null)?.spots_taken as number ?? 4;
      setPosition(pos);

      // Tier rates
      const tierRates: Record<string, { monthly: number; standard: number }> = {
        ignition: { monthly: 1250, standard: 2500 },
        velocity: { monthly: 2500, standard: 5000 },
        spark: { monthly: 625, standard: 1250 },
      };
      const tierKey = (clientRow.tier || "ignition").toLowerCase();
      const rates = tierRates[tierKey] || tierRates.ignition;
      setMonthlyRate(rates.monthly);
      setStandardRate(rates.standard);
      setTier(
        clientRow.tier
          ? clientRow.tier.charAt(0).toUpperCase() + clientRow.tier.slice(1)
          : "Ignition"
      );
      setClient(clientRow as unknown as ClientData);
      setLoading(false);
    }

    checkState();
  }, [router, supabase]);

  if (loading) {
    return (
      <div
        style={{
          background: "#F7F3EE",
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "11px",
          letterSpacing: "0.1em",
          color: "#7A756D",
        }}
      >
        loading...
      </div>
    );
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400;1,700&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
          --cream:   #F7F3EE;
          --surface: #EDE8E0;
          --ink:     #0C0A08;
          --ink-2:   #2E2B26;
          --ink-3:   #7A756D;
          --amber:   #D4956A;
          --amber-b: rgba(212,149,106,0.28);
          --amber-d: rgba(212,149,106,0.10);
          --rule:    rgba(12,10,8,0.08);
          --rule-2:  rgba(12,10,8,0.14);
          --rule-i:  rgba(255,255,255,0.08);
        }

        .welcome-body {
          background: var(--cream);
          color: var(--ink);
          font-family: 'DM Sans', sans-serif;
          font-weight: 300;
          min-height: 100vh;
          overflow-x: hidden;
        }

        .topbar {
          position: fixed; top: 0; left: 0; right: 0;
          background: rgba(247,243,238,.92);
          backdrop-filter: blur(10px);
          border-bottom: 1px solid var(--rule);
          z-index: 100;
          padding: 20px 56px;
          display: flex; align-items: center; justify-content: space-between;
        }

        .logo {
          font-family: 'JetBrains Mono', monospace;
          font-size: 13px; letter-spacing: .18em; text-transform: uppercase;
          color: var(--ink);
        }

        .topbar-status {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px; letter-spacing: .12em; text-transform: uppercase;
          color: var(--ink-3);
          display: flex; align-items: center; gap: 8px;
        }

        .topbar-status::before {
          content: ''; width: 6px; height: 6px; border-radius: 50%;
          background: var(--amber);
          box-shadow: 0 0 0 3px rgba(212,149,106,.18);
          animation: pulse 2.4s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 3px rgba(212,149,106,.18); }
          50% { box-shadow: 0 0 0 5px rgba(212,149,106,.08); }
        }

        .hero {
          max-width: 1100px;
          margin: 0 auto;
          padding: 160px 56px 100px;
          display: grid;
          grid-template-columns: 1.15fr 1fr;
          gap: 88px;
          align-items: start;
        }

        .confirm-badge {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          padding: 10px 20px 10px 14px;
          background: rgba(212,149,106,.1);
          border: 1px solid var(--amber-b);
          margin-bottom: 36px;
          animation: fadeUp .8s cubic-bezier(.2,.8,.2,1);
        }

        .confirm-badge-icon {
          width: 20px; height: 20px;
          border-radius: 50%;
          background: var(--amber);
          display: flex; align-items: center; justify-content: center;
          color: var(--ink);
          flex-shrink: 0;
        }

        .confirm-badge-text {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
          color: var(--amber);
          font-weight: 500;
        }

        .hero-h1 {
          font-family: 'Playfair Display', serif;
          font-size: clamp(44px, 5vw, 68px);
          line-height: 1.06;
          letter-spacing: -.025em;
          font-weight: 700;
          margin-bottom: 32px;
          animation: fadeUp .9s .1s cubic-bezier(.2,.8,.2,1) backwards;
        }

        .hero-h1 em { font-style: italic; color: var(--amber); }

        .hero-sub {
          font-size: 18px;
          font-weight: 300;
          color: var(--ink-2);
          line-height: 1.7;
          max-width: 500px;
          margin-bottom: 48px;
          animation: fadeUp 1s .2s cubic-bezier(.2,.8,.2,1) backwards;
        }

        .cta-block {
          display: flex;
          flex-direction: column;
          gap: 14px;
          align-items: flex-start;
          animation: fadeUp 1.1s .3s cubic-bezier(.2,.8,.2,1) backwards;
        }

        .btn-primary {
          display: inline-flex;
          align-items: center;
          gap: 14px;
          padding: 20px 44px;
          font-family: 'DM Sans', sans-serif;
          font-size: 15px;
          font-weight: 500;
          letter-spacing: .02em;
          background: var(--ink);
          color: var(--cream);
          text-decoration: none;
          border: none;
          cursor: pointer;
          transition: all .3s cubic-bezier(.2,.8,.2,1);
          position: relative;
          overflow: hidden;
        }

        .btn-primary:hover { background: var(--amber); color: var(--ink); }

        .cta-fine {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: .08em;
          color: var(--ink-3);
        }

        .receipt {
          background: var(--ink);
          color: var(--cream);
          padding: 40px 44px;
          position: relative;
          animation: fadeUp 1s .4s cubic-bezier(.2,.8,.2,1) backwards;
        }

        .receipt::before {
          content: '';
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 2px;
          background: var(--amber);
        }

        .receipt-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: .2em;
          text-transform: uppercase;
          color: rgba(247,243,238,.55);
          margin-bottom: 8px;
        }

        .receipt-name {
          font-family: 'Playfair Display', serif;
          font-size: 22px;
          font-weight: 700;
          color: #F7F3EE;
          margin-bottom: 4px;
        }

        .receipt-tier {
          font-size: 13px;
          color: var(--amber);
          font-style: italic;
          margin-bottom: 28px;
        }

        .receipt-rows {
          border-top: 1px solid var(--rule-i);
          padding-top: 22px;
          margin-bottom: 24px;
        }

        .receipt-row {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          padding: 11px 0;
          border-bottom: 1px solid var(--rule-i);
        }

        .receipt-row:last-child { border-bottom: none; }

        .receipt-row .l {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: .12em;
          text-transform: uppercase;
          color: rgba(247,243,238,.52);
        }

        .receipt-row .v {
          font-size: 13px;
          color: #F7F3EE;
        }

        .receipt-row .v.amber {
          color: var(--amber);
          font-family: 'JetBrains Mono', monospace;
          font-weight: 500;
        }

        .receipt-row .v.struck {
          text-decoration: line-through;
          opacity: 0.5;
        }

        .receipt-foot {
          padding-top: 22px;
          border-top: 1px solid var(--rule-i);
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: .08em;
          color: rgba(247,243,238,.58);
          line-height: 1.6;
        }

        .receipt-foot b {
          color: #F7F3EE;
          font-weight: 500;
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .div-rule {
          border: none;
          border-top: 1px solid var(--rule);
          margin: 0 56px;
        }

        .next {
          max-width: 1100px;
          margin: 0 auto;
          padding: 92px 56px;
        }

        .next-eyebrow {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: .2em;
          text-transform: uppercase;
          color: var(--ink-3);
          display: flex;
          align-items: center;
          gap: 14px;
          margin-bottom: 20px;
        }

        .next-eyebrow::after {
          content: '';
          width: 40px;
          height: 1px;
          background: var(--rule-2);
        }

        .next-h {
          font-family: 'Playfair Display', serif;
          font-size: clamp(32px, 3.2vw, 44px);
          font-weight: 700;
          line-height: 1.12;
          letter-spacing: -.02em;
          max-width: 720px;
          margin-bottom: 56px;
        }

        .next-h em { font-style: italic; color: var(--amber); }

        .timeline {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1px;
          background: var(--rule);
          border: 1px solid var(--rule);
        }

        .timeline-step {
          background: var(--cream);
          padding: 40px 32px;
          transition: background .3s;
        }

        .timeline-step:hover { background: var(--surface); }

        .ts-when {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: .16em;
          text-transform: uppercase;
          color: var(--amber);
          margin-bottom: 18px;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .ts-when::before {
          content: '';
          width: 6px; height: 6px;
          border-radius: 50%;
          background: var(--amber);
          flex-shrink: 0;
        }

        .ts-h {
          font-size: 15px;
          font-weight: 500;
          color: var(--ink);
          margin-bottom: 12px;
          line-height: 1.4;
        }

        .ts-p {
          font-size: 13px;
          color: var(--ink-3);
          line-height: 1.72;
        }

        .founder-strip {
          background: var(--surface);
          padding: 80px 56px;
        }

        .founder-inner {
          max-width: 920px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: auto 1fr;
          gap: 52px;
          align-items: center;
        }

        .founder-avatar {
          width: 88px; height: 88px;
          border-radius: 50%;
          background: var(--ink);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          border: 1px solid var(--amber-b);
        }

        .founder-initial {
          font-family: 'JetBrains Mono', monospace;
          font-size: 26px;
          font-weight: 500;
          color: var(--amber);
          letter-spacing: .04em;
        }

        .founder-quote {
          font-family: 'Playfair Display', serif;
          font-style: italic;
          font-size: clamp(18px, 2vw, 22px);
          line-height: 1.55;
          color: var(--ink-2);
          margin-bottom: 20px;
        }

        .founder-meta {
          display: flex;
          align-items: center;
          gap: 16px;
          flex-wrap: wrap;
        }

        .founder-name {
          font-size: 14px;
          font-weight: 500;
          color: var(--ink);
        }

        .founder-role {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: .1em;
          color: var(--amber);
        }

        .founder-contact {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: .04em;
          color: var(--ink-3);
        }

        .founder-contact a {
          color: var(--ink-3);
          text-decoration: none;
          transition: color .2s;
        }

        .founder-contact a:hover { color: var(--amber); }

        .secondary-cta {
          padding: 96px 56px;
          text-align: center;
        }

        .secondary-cta-inner { max-width: 620px; margin: 0 auto; }

        .secondary-cta h2 {
          font-family: 'Playfair Display', serif;
          font-size: clamp(28px, 3vw, 40px);
          font-weight: 700;
          line-height: 1.14;
          letter-spacing: -.02em;
          margin-bottom: 20px;
        }

        .secondary-cta h2 em { font-style: italic; color: var(--amber); }

        .secondary-cta p {
          font-size: 15px;
          color: var(--ink-3);
          line-height: 1.75;
          margin-bottom: 36px;
        }

        .secondary-cta-actions {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 14px;
        }

        .secondary-cta-sub {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: .08em;
          color: var(--ink-3);
        }

        .site-footer {
          background: var(--ink);
          padding: 28px 56px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-top: 1px solid rgba(255,255,255,.05);
        }

        .foot-logo {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11px;
          letter-spacing: .16em;
          text-transform: uppercase;
          color: rgba(247,243,238,.52);
        }

        .foot-legal {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: .1em;
          color: rgba(247,243,238,.42);
        }

        @media (max-width: 900px) {
          .topbar { padding: 18px 24px; }
          .hero {
            grid-template-columns: 1fr;
            padding: 130px 24px 72px;
            gap: 52px;
          }
          .div-rule { margin: 0 24px; }
          .next { padding: 64px 24px; }
          .timeline { grid-template-columns: 1fr 1fr; }
          .founder-strip { padding: 56px 24px; }
          .founder-inner { grid-template-columns: 1fr; gap: 28px; text-align: center; }
          .founder-avatar { margin: 0 auto; }
          .founder-meta { justify-content: center; }
          .secondary-cta { padding: 64px 24px; }
          .site-footer { flex-direction: column; gap: 12px; text-align: center; padding: 24px; }
          .receipt { padding: 32px 28px; }
        }

        @media (max-width: 580px) {
          .timeline { grid-template-columns: 1fr; }
        }
      `}</style>

      <div className="welcome-body">
        {/* TOP BAR */}
        <div className="topbar">
          <div className="logo">
            Agency<span style={{ color: "#D4956A" }}>OS</span>
          </div>
          <div className="topbar-status">
            Founding member · #{position} of 20
          </div>
        </div>

        {/* HERO */}
        <div className="hero">
          <div>
            <div className="confirm-badge">
              <div className="confirm-badge-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ width: 12, height: 12 }}>
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <div className="confirm-badge-text">Deposit confirmed · $500 AUD</div>
            </div>

            <h1 className="hero-h1">
              You&apos;re in.<br />
              <em>Let&apos;s build your cycle.</em>
            </h1>

            <p className="hero-sub">
              Your founding position is reserved. Your 50% lifetime discount is
              locked in. Everything from here is setup — connecting your systems,
              confirming your agency, and starting your first cycle. Takes about
              15 minutes. I&apos;ll walk you through it personally if you want.
            </p>

            <div className="cta-block">
              <Link href="/onboarding/crm" className="btn-primary">
                <span>Begin setup</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 18, height: 18 }}>
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </Link>
              <span className="cta-fine">5 steps · 15 minutes · Cycle starts the day you finish</span>
            </div>
          </div>

          {/* RECEIPT CARD */}
          <div className="receipt">
            <div className="receipt-label">Your founding position</div>
            <div className="receipt-name">Agency OS — {tier}</div>
            <div className="receipt-tier">Founding rate · Locked for life</div>

            <div className="receipt-rows">
              <div className="receipt-row">
                <div className="l">Deposit</div>
                <div className="v amber">$500 AUD</div>
              </div>
              <div className="receipt-row">
                <div className="l">Monthly rate</div>
                <div className="v">${monthlyRate.toLocaleString()} AUD / mo</div>
              </div>
              <div className="receipt-row">
                <div className="l">Standard rate</div>
                <div className="v struck">${standardRate.toLocaleString()} AUD / mo</div>
              </div>
              <div className="receipt-row">
                <div className="l">Your savings</div>
                <div className="v amber">50% · Forever</div>
              </div>
              <div className="receipt-row">
                <div className="l">Cycle volume</div>
                <div className="v">600 prospects / month</div>
              </div>
              <div className="receipt-row">
                <div className="l">Founding position</div>
                <div className="v amber">#{position} of 20</div>
              </div>
            </div>

            <div className="receipt-foot">
              <b>Refundable at any time</b> before your first cycle goes live.
              Reply to any email from me and I&apos;ll process it the same day.
              No conditions, no friction, no exit fees.
            </div>
          </div>
        </div>

        <hr className="div-rule" />

        {/* WHAT HAPPENS NEXT */}
        <div className="next">
          <div className="next-eyebrow">What happens next</div>
          <h2 className="next-h">
            From deposit to your first <em>booked meeting.</em>
          </h2>

          <div className="timeline">
            <div className="timeline-step">
              <div className="ts-when">Right now · 15 min</div>
              <div className="ts-h">Complete setup</div>
              <div className="ts-p">
                Connect HubSpot so we can protect your existing clients.
                Connect LinkedIn so we can send as you. Confirm your services.
                Select your target area.
              </div>
            </div>

            <div className="timeline-step">
              <div className="ts-when">Day 1 · Within 30 min</div>
              <div className="ts-h">First prospects appear</div>
              <div className="ts-p">
                Discovery runs across your target area. Enrichment scores every
                prospect. Your dashboard populates with the first wave — visible,
                inspectable, nothing sent yet.
              </div>
            </div>

            <div className="timeline-step">
              <div className="ts-when">Day 1 · Within 2 hours</div>
              <div className="ts-h">First drafts ready</div>
              <div className="ts-p">
                Personalised outreach drafts appear across email, LinkedIn, and
                voice AI for each prospect. Every draft references their actual
                business. Review and release when you&apos;re ready.
              </div>
            </div>

            <div className="timeline-step">
              <div className="ts-when">Day 7-14 · First meetings</div>
              <div className="ts-h">Meetings land in HubSpot</div>
              <div className="ts-p">
                When a prospect books, the contact + deal + calendar event + full
                briefing document lands in your HubSpot automatically. Ready for
                your sales process.
              </div>
            </div>
          </div>
        </div>

        {/* FOUNDER STRIP */}
        <div className="founder-strip">
          <div className="founder-inner">
            <div className="founder-avatar">
              <span className="founder-initial">D</span>
            </div>
            <div>
              <p className="founder-quote">
                &ldquo;Founding customers aren&apos;t a marketing tier to me —
                they&apos;re the people who shaped what this became. You have my
                direct line, and I mean that literally. Anything you need, you
                come to me.&rdquo;
              </p>
              <div className="founder-meta">
                <span className="founder-name">Dave — Founder, Agency OS</span>
                <span className="founder-role">Sydney, Australia</span>
                <span className="founder-contact">
                  <a href="mailto:dave@agencyxos.ai">dave@agencyxos.ai</a>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* SECONDARY CTA */}
        <div className="secondary-cta">
          <div className="secondary-cta-inner">
            <h2>
              Ready when you are.<br />
              <em>Let&apos;s get you live.</em>
            </h2>
            <p>
              The sooner your setup is complete, the sooner your cycle starts.
              Most founding customers finish in one sitting over a coffee. Takes
              15 minutes.
            </p>
            <div className="secondary-cta-actions">
              <Link href="/onboarding/crm" className="btn-primary" style={{ padding: "18px 40px" }}>
                <span>Begin setup</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 18, height: 18 }}>
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </Link>
              <span className="secondary-cta-sub">
                Or reply to the email I just sent — I&apos;ll walk you through it
              </span>
            </div>
          </div>
        </div>

        {/* FOOTER */}
        <footer className="site-footer">
          <div className="foot-logo">
            Agency<span style={{ color: "#D4956A", fontStyle: "normal" }}>OS</span>
          </div>
          <div className="foot-legal">
            Founding cohort · Sydney, Australia · April 2026
          </div>
        </footer>
      </div>
    </>
  );
}
