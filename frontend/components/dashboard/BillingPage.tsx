/**
 * BillingPage.tsx - Billing & Subscription Page Component
 * Phase: Operation Modular Cockpit
 *
 * Ported from billing-v2.html
 * Features:
 * - Current plan display with metrics
 * - Three pricing tiers (Spark, Ignition, Velocity)
 * - Usage meters (leads contacted, meetings booked, clients won)
 * - Upgrade/downgrade buttons
 * - Invoice history table
 * - Payment method section
 * - Bloomberg dark mode + glassmorphic styling
 */

"use client";

import { useState } from "react";
import {
  Zap,
  Users,
  Calendar,
  User,
  Lightbulb,
  Check,
  CreditCard,
  TrendingUp,
  BarChart3,
  HelpCircle,
  Download,
  FileText,
  ArrowUpRight,
  Star,
  Link2,
  Bell,
  Database,
} from "lucide-react";

// ============================================
// Types
// ============================================

type PlanTier = "spark" | "ignition" | "velocity";

interface PlanDetails {
  id: PlanTier;
  name: string;
  tagline: string;
  price: number;
  leads: number;
  meetingsRange: string;
  clientsRange: string;
  features: string[];
}

interface UsageData {
  leadsContacted: number;
  leadsLimit: number;
  meetingsBooked: number;
  meetingsTarget: string;
  clientsWon: number;
  clientsTarget: string;
}

interface Invoice {
  id: string;
  date: string;
  description: string;
  amount: number;
  status: "paid" | "pending";
}

interface PaymentMethod {
  type: "visa" | "mastercard" | "amex";
  last4: string;
  expiryMonth: string;
  expiryYear: string;
}

// ============================================
// Constants
// ============================================

const PLANS: PlanDetails[] = [
  {
    id: "spark",
    name: "Spark",
    tagline: "Launch your outbound engine",
    price: 750,
    leads: 150,
    meetingsRange: "N/A",
    clientsRange: "N/A",
    features: [
      "150 records per month",
      "All 4 outreach channels",
      "Full AI intelligence",
      "Haiku personalisation",
    ],
  },
  {
    id: "ignition",
    name: "Ignition",
    tagline: "Grow your pipeline",
    price: 2500,
    leads: 600,
    meetingsRange: "8-9",
    clientsRange: "1-2",
    features: [
      "600 records per month",
      "All 4 outreach channels",
      "Full AI intelligence",
      "Haiku personalisation",
    ],
  },
  {
    id: "velocity",
    name: "Velocity",
    tagline: "Maximum pipeline capacity",
    price: 5000,
    leads: 1500,
    meetingsRange: "15-16",
    clientsRange: "3-4",
    features: [
      "1,500 records per month",
      "All 4 outreach channels",
      "Full AI intelligence",
      "Haiku personalisation",
    ],
  },
];

const MOCK_USAGE: UsageData = {
  leadsContacted: 1847,
  leadsLimit: 1500,
  meetingsBooked: 12,
  meetingsTarget: "15-16",
  clientsWon: 3,
  clientsTarget: "3-4",
};

const MOCK_INVOICES: Invoice[] = [
  { id: "inv-001", date: "Feb 1, 2026", description: "Velocity Plan — Monthly", amount: 5000, status: "paid" },
  { id: "inv-002", date: "Jan 1, 2026", description: "Velocity Plan — Monthly", amount: 5000, status: "paid" },
  { id: "inv-003", date: "Dec 1, 2025", description: "Velocity Plan — Monthly", amount: 5000, status: "paid" },
  { id: "inv-004", date: "Nov 1, 2025", description: "Ignition Plan — Monthly", amount: 2500, status: "paid" },
];

const MOCK_PAYMENT_METHOD: PaymentMethod = {
  type: "mastercard",
  last4: "8492",
  expiryMonth: "09",
  expiryYear: "28",
};

// ============================================
// Sub-Components
// ============================================

/**
 * Card wrapper with glassmorphic styling
 */
function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-bg-surface border border-default rounded-2xl overflow-hidden ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Card header with title and optional right element
 */
function CardHeader({
  icon,
  title,
  subtitle,
  rightElement,
}: {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  rightElement?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-6 py-5 border-b border-default">
      <div className="flex items-center gap-2.5">
        {icon && <span className="text-amber">{icon}</span>}
        <span className="font-semibold text-ink">{title}</span>
      </div>
      {subtitle && <span className="text-sm text-ink-3">{subtitle}</span>}
      {rightElement}
    </div>
  );
}

/**
 * Usage meter component with progress bar
 */
function UsageMeter({
  label,
  current,
  total,
  icon,
  colorClass,
  barColorClass,
  statusText,
}: {
  label: string;
  current: number | string;
  total: string;
  icon: React.ReactNode;
  colorClass: string;
  barColorClass: string;
  statusText: React.ReactNode;
}) {
  const currentNum = typeof current === "number" ? current : parseInt(current, 10);
  const totalNum = parseInt(total.split("-")[0].replace(/[^0-9]/g, ""), 10);
  const percentage = Math.min((currentNum / totalNum) * 100, 100);

  return (
    <div className="bg-bg-elevated rounded-xl p-5">
      <div className="flex justify-between items-start mb-4">
        <span className="font-semibold text-ink text-sm">{label}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colorClass}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline gap-1 mb-3">
        <span className="text-3xl font-extrabold font-mono text-ink">
          {typeof current === "number" ? current.toLocaleString() : current}
        </span>
        <span className="text-base text-ink-3 font-mono">/ {total}</span>
      </div>
      <div className="h-2 bg-bg-elevated rounded-full overflow-hidden mb-2">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-sm text-ink-3">{statusText}</div>
    </div>
  );
}

/**
 * Plan comparison card
 */
function PlanCard({
  plan,
  currentPlan,
  isRecommended,
  onSelect,
}: {
  plan: PlanDetails;
  currentPlan: PlanTier;
  isRecommended: boolean;
  onSelect: (plan: PlanTier) => void;
}) {
  const isCurrent = plan.id === currentPlan;
  const isDowngrade = PLANS.findIndex((p) => p.id === plan.id) < PLANS.findIndex((p) => p.id === currentPlan);

  return (
    <div
      className={`
        relative rounded-2xl p-7 text-center transition-all duration-200
        ${isCurrent
          ? "bg-bg-elevated border-2 border-amber"
          : isRecommended
          ? "bg-gradient-to-b from-amber/10 to-[#1A1A28] border-2 border-amber"
          : "bg-bg-elevated border-2 border-default hover:border-default"
        }
      `}
    >
      {/* Top gradient bar for recommended */}
      {isRecommended && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber to-amber-light rounded-t-2xl" />
      )}

      {/* Badge */}
      {(isCurrent || isRecommended) && (
        <span
          className={`
            inline-block px-3.5 py-1.5 text-xs font-bold uppercase tracking-wide rounded-full mb-4
            ${isCurrent
              ? "bg-amber-glow text-amber border border-amber"
              : "bg-amber text-ink"
            }
          `}
        >
          {isCurrent ? "Current Plan" : "Recommended"}
        </span>
      )}

      <h3 className="text-2xl font-bold text-ink mb-2">{plan.name}</h3>
      <p className="text-sm text-ink-3 mb-4">{plan.tagline}</p>
      <div className="text-4xl font-extrabold font-mono text-ink mb-1">
        ${plan.price.toLocaleString()}
        <span className="text-sm font-normal text-ink-3">/mo</span>
      </div>

      {/* Outcomes preview */}
      <div className="flex justify-center gap-3 md:gap-6 my-5 p-4 bg-bg-surface rounded-lg">
        <div className="text-center">
          <div className="text-xl font-bold font-mono text-ink">{plan.meetingsRange}</div>
          <div className="text-xs text-ink-3 uppercase tracking-wide">Meetings/mo</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold font-mono text-ink">{plan.clientsRange}</div>
          <div className="text-xs text-ink-3 uppercase tracking-wide">New Clients</div>
        </div>
      </div>

      {/* Features list */}
      <ul className="text-left space-y-2.5 mb-6">
        {plan.features.map((feature, idx) => (
          <li key={idx} className="flex items-start gap-2.5 text-sm text-ink-2">
            <Check className="w-4 h-4 text-amber flex-shrink-0 mt-0.5" />
            {feature}
          </li>
        ))}
      </ul>

      {/* Action button */}
      <button
        onClick={() => !isCurrent && onSelect(plan.id)}
        disabled={isCurrent}
        className={`
          w-full py-3.5 px-4 rounded-lg font-semibold text-sm transition-all
          ${isCurrent
            ? "bg-amber-glow text-amber border border-amber cursor-default"
            : isRecommended
            ? "bg-amber text-ink hover:bg-violet-400 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber/30"
            : "bg-bg-surface text-ink-3 border border-default hover:bg-bg-elevated hover:text-ink-2"
          }
        `}
      >
        {isCurrent ? "Current Plan" : isDowngrade ? "Downgrade" : `Upgrade to ${plan.name}`}
      </button>
    </div>
  );
}

/**
 * Invoice table row
 */
function InvoiceRow({ invoice }: { invoice: Invoice }) {
  return (
    <tr className="hover:bg-bg-elevated transition-colors">
      <td className="px-6 py-4 font-mono text-ink">{invoice.date}</td>
      <td className="px-6 py-4 text-ink-2">{invoice.description}</td>
      <td className="px-6 py-4 font-mono font-semibold text-ink">
        ${invoice.amount.toLocaleString()}.00
      </td>
      <td className="px-6 py-4">
        <span
          className={`
            inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
            ${invoice.status === "paid"
              ? "bg-amber/15 text-amber"
              : "bg-amber-500/15 text-amber-400"
            }
          `}
        >
          <Check className="w-3 h-3" />
          {invoice.status === "paid" ? "Paid" : "Pending"}
        </span>
      </td>
      <td className="px-6 py-4">
        <button className="text-amber text-sm font-medium hover:underline">
          Download
        </button>
      </td>
    </tr>
  );
}

/**
 * Mastercard SVG icon
 */
function MastercardIcon() {
  return (
    <svg viewBox="0 0 32 20" className="w-8 h-5">
      <rect width="32" height="20" rx="2" fill="#1A1F71" />
      <circle cx="12" cy="10" r="6" fill="#EB001B" />
      <circle cx="20" cy="10" r="6" fill="#F79E1B" />
      <path d="M16 5.3a6 6 0 010 9.4 6 6 0 000-9.4z" fill="#FF5F00" />
    </svg>
  );
}

// ============================================
// Main Component
// ============================================

export default function BillingPage() {
  const [currentPlan] = useState<PlanTier>("velocity");
  const [usage] = useState<UsageData>(MOCK_USAGE);
  const [invoices] = useState<Invoice[]>(MOCK_INVOICES);
  const [paymentMethod] = useState<PaymentMethod>(MOCK_PAYMENT_METHOD);

  const currentPlanDetails = PLANS.find((p) => p.id === currentPlan)!;
  const leadsRemaining = usage.leadsLimit - usage.leadsContacted;

  const handlePlanSelect = (planId: PlanTier) => {
    // TODO: Integrate with payment/subscription API
    console.log("Plan selected:", planId);
  };

  return (
    <div className="min-h-screen bg-bg-cream">
      {/* Header */}
      <header className="bg-bg-surface border-b border-default px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink">Billing & Subscription</h1>
          <p className="text-sm text-ink-3 mt-1">
            Manage your plan, usage, and payment methods
          </p>
        </div>
        <button className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-ink-2 border border-default rounded-lg hover:bg-bg-elevated hover:text-ink transition-colors">
          <HelpCircle className="w-4 h-4" />
          Support
        </button>
      </header>

      <div className="max-w-[1200px] px-8 py-8 space-y-6">
        {/* Current Plan Hero */}
        <Card className="relative">
          {/* Top accent bar */}
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber to-amber-light" />

          <div className="p-8">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-ink flex items-center gap-3">
                  <Zap className="w-7 h-7 text-amber" />
                  {currentPlanDetails.name} Plan
                </h2>
                <p className="text-sm text-ink-3 mt-1">
                  Your subscription renews on{" "}
                  <strong className="text-ink">March 1, 2026</strong>
                </p>
                <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 mt-3 bg-amber/15 text-amber text-xs font-semibold rounded-full">
                  <Check className="w-3.5 h-3.5" />
                  Active
                </span>
              </div>
              <div className="text-right">
                <div className="text-5xl font-extrabold font-mono text-ink">
                  ${currentPlanDetails.price.toLocaleString()}
                </div>
                <div className="text-sm text-ink-3 mt-1">per month</div>
              </div>
            </div>

            {/* Plan metrics */}
            <div className="grid grid-cols-4 gap-4 my-7 py-6 border-y border-default">
              <div className="flex items-center gap-3 px-4 py-3.5 bg-bg-elevated rounded-lg">
                <div className="w-10 h-10 bg-amber/15 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-amber" />
                </div>
                <div className="text-sm text-ink-2">
                  <strong className="block text-lg font-bold font-mono text-ink">
                    {currentPlanDetails.leads.toLocaleString()}
                  </strong>
                  Leads per month
                </div>
              </div>
              <div className="flex items-center gap-3 px-4 py-3.5 bg-bg-elevated rounded-lg">
                <div className="w-10 h-10 bg-amber-glow rounded-lg flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-amber" />
                </div>
                <div className="text-sm text-ink-2">
                  <strong className="block text-lg font-bold font-mono text-ink">
                    {currentPlanDetails.meetingsRange}
                  </strong>
                  Meetings per month
                </div>
              </div>
              <div className="flex items-center gap-3 px-4 py-3.5 bg-bg-elevated rounded-lg">
                <div className="w-10 h-10 bg-bg-elevated/15 rounded-lg flex items-center justify-center">
                  <User className="w-5 h-5 text-ink-2" />
                </div>
                <div className="text-sm text-ink-2">
                  <strong className="block text-lg font-bold font-mono text-ink">
                    {currentPlanDetails.clientsRange}
                  </strong>
                  New clients per month
                </div>
              </div>
              <div className="flex items-center gap-3 px-4 py-3.5 bg-bg-elevated rounded-lg">
                <div className="w-10 h-10 bg-amber-500/15 rounded-lg flex items-center justify-center">
                  <Lightbulb className="w-5 h-5 text-amber-400" />
                </div>
                <div className="text-sm text-ink-2">
                  <strong className="block text-lg font-bold font-mono text-ink">
                    5-Channel
                  </strong>
                  Outreach system
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <button className="flex items-center gap-2 px-5 py-2.5 bg-amber text-ink font-medium rounded-lg hover:bg-violet-400 hover:-translate-y-0.5 transition-all">
                <TrendingUp className="w-4 h-4" />
                Upgrade Plan
              </button>
              <button className="flex items-center gap-2 px-5 py-2.5 text-ink-2 border border-default rounded-lg hover:bg-bg-elevated hover:text-ink transition-colors">
                <CreditCard className="w-4 h-4" />
                Update Payment
              </button>
              <button className="px-5 py-2.5 text-ink-2 border border-default rounded-lg hover:bg-bg-elevated hover:text-ink transition-colors">
                Cancel Subscription
              </button>
            </div>
          </div>
        </Card>

        {/* Usage This Month */}
        <Card>
          <CardHeader
            icon={<BarChart3 className="w-5 h-5" />}
            title="Usage This Month"
            subtitle="Resets March 1, 2026"
          />
          <div className="p-6">
            <div className="grid grid-cols-3 gap-3 md:gap-6">
              <UsageMeter
                label="Leads Contacted"
                current={usage.leadsContacted}
                total={usage.leadsLimit.toLocaleString()}
                icon={<Users className="w-4.5 h-4.5 text-amber" />}
                colorClass="bg-amber/15"
                barColorClass="bg-gradient-to-r from-amber to-amber-light"
                statusText={
                  <>
                    <strong className="text-amber">{leadsRemaining.toLocaleString()}</strong> leads remaining
                  </>
                }
              />
              <UsageMeter
                label="Meetings Booked"
                current={usage.meetingsBooked}
                total={usage.meetingsTarget}
                icon={<Calendar className="w-4.5 h-4.5 text-amber" />}
                colorClass="bg-amber-glow"
                barColorClass="bg-gradient-to-r from-amber to-amber"
                statusText={
                  <>
                    <strong className="text-amber">On track</strong> for target
                  </>
                }
              />
              <UsageMeter
                label="New Clients Won"
                current={usage.clientsWon}
                total={usage.clientsTarget}
                icon={<Check className="w-4.5 h-4.5 text-amber" />}
                colorClass="bg-amber/15"
                barColorClass="bg-gradient-to-r from-amber to-amber"
                statusText={
                  <>
                    <strong className="text-amber">Exceeding</strong> expectations
                  </>
                }
              />
            </div>
          </div>
        </Card>

        {/* API & Integrations */}
        <Card>
          <CardHeader
            icon={<Link2 className="w-5 h-5" />}
            title="API & Integrations"
            rightElement={
              <button className="text-amber text-sm font-medium hover:underline">
                View documentation
              </button>
            }
          />
          <div className="p-6">
            <div className="grid grid-cols-3 gap-5">
              <div className="flex gap-3.5 p-5 bg-bg-elevated rounded-xl">
                <div className="w-11 h-11 bg-bg-elevated/15 rounded-lg flex items-center justify-center flex-shrink-0">
                  <ArrowUpRight className="w-5 h-5 text-ink-2" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-ink mb-1">Connect Your CRM</h4>
                  <p className="text-sm text-ink-3 leading-relaxed">
                    Sync leads bidirectionally with HubSpot, Salesforce, Pipedrive, and more.
                  </p>
                </div>
              </div>
              <div className="flex gap-3.5 p-5 bg-bg-elevated rounded-xl">
                <div className="w-11 h-11 bg-bg-elevated/15 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Bell className="w-5 h-5 text-ink-2" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-ink mb-1">Meeting Webhooks</h4>
                  <p className="text-sm text-ink-3 leading-relaxed">
                    Receive instant notifications when new meetings are booked.
                  </p>
                </div>
              </div>
              <div className="flex gap-3.5 p-5 bg-bg-elevated rounded-xl">
                <div className="w-11 h-11 bg-bg-elevated/15 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Database className="w-5 h-5 text-ink-2" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-ink mb-1">Lead Data Sync</h4>
                  <p className="text-sm text-ink-3 leading-relaxed">
                    Export enriched lead data and engagement history to your systems.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Payment Method */}
        <Card>
          <CardHeader
            icon={<CreditCard className="w-5 h-5" />}
            title="Payment Method"
            rightElement={
              <button className="text-amber text-sm font-medium hover:underline">
                Add new
              </button>
            }
          />
          <div className="p-6">
            <div className="flex items-center justify-between p-5 bg-bg-elevated rounded-xl">
              <div className="flex items-center gap-4">
                <div className="w-14 h-9 bg-bg-elevated border border-default rounded flex items-center justify-center">
                  <MastercardIcon />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-ink">
                    {paymentMethod.type.charAt(0).toUpperCase() + paymentMethod.type.slice(1)} ending in{" "}
                    {paymentMethod.last4}
                  </h4>
                  <p className="text-sm text-ink-3 font-mono mt-0.5">
                    Expires {paymentMethod.expiryMonth}/{paymentMethod.expiryYear}
                  </p>
                </div>
              </div>
              <button className="px-4 py-2 text-sm text-ink-2 border border-default rounded-lg hover:bg-bg-elevated hover:text-ink transition-colors">
                Update
              </button>
            </div>
          </div>
        </Card>

        {/* Invoice History */}
        <Card>
          <CardHeader
            icon={<FileText className="w-5 h-5" />}
            title="Invoice History"
            rightElement={
              <button className="text-amber text-sm font-medium hover:underline flex items-center gap-1">
                <Download className="w-4 h-4" />
                Download all
              </button>
            }
          />
          <table className="w-full">
            <thead>
              <tr className="bg-bg-elevated border-b border-default">
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-ink-3 uppercase tracking-wide">
                  Date
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-ink-3 uppercase tracking-wide">
                  Description
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-ink-3 uppercase tracking-wide">
                  Amount
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-ink-3 uppercase tracking-wide">
                  Status
                </th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-ink-3 uppercase tracking-wide" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E1E2E]">
              {invoices.map((invoice) => (
                <InvoiceRow key={invoice.id} invoice={invoice} />
              ))}
            </tbody>
          </table>
        </Card>

        {/* Available Plans */}
        <Card>
          <CardHeader icon={<TrendingUp className="w-5 h-5" />} title="Available Plans" />
          <div className="p-6">
            <div className="grid grid-cols-3 gap-5">
              {PLANS.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  currentPlan={currentPlan}
                  isRecommended={plan.id === "velocity"}
                  onSelect={handlePlanSelect}
                />
              ))}
            </div>
          </div>
        </Card>

        {/* Upgrade CTA */}
        <div className="bg-gradient-to-r from-amber-500/10 to-amber-400/5 border border-amber-500/25 rounded-2xl p-8 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-ink flex items-center gap-2.5 mb-2">
              <Star className="w-6 h-6 text-amber-400" />
              Ready to dominate your market?
            </h3>
            <p className="text-sm text-ink-2 max-w-lg">
              Upgrade to Velocity and get more records per month with all 4 outreach channels running
              at full capacity.
            </p>
          </div>
          <button className="flex items-center gap-2 px-7 py-3.5 bg-gradient-to-r from-amber-500 to-amber-400 text-[#0A0A12] font-semibold rounded-lg hover:shadow-lg hover:shadow-amber-500/30 transition-all">
            <Zap className="w-5 h-5" />
            Talk to Sales
          </button>
        </div>
      </div>
    </div>
  );
}
