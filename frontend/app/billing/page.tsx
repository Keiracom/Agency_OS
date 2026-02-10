'use client';

import { HelpCircle } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';
import {
  PlanHeroCard,
  UsageMeters,
  InvoiceTable,
  PaymentMethod,
  PlanComparison,
  UpgradeCTA,
} from '@/components/billing';
import {
  mockCurrentPlan,
  mockPlanMetrics,
  mockUsageData,
  mockInvoices,
  mockPaymentMethod,
  mockAvailablePlans,
} from '@/data/mock-billing';

export default function BillingPage() {
  return (
    <AppShell pageTitle="Billing & Subscription">
      {/* Header Row with Subtitle and Support */}
      <div className="px-6 pt-2 pb-0 flex items-center justify-between">
        <p className="text-sm text-text-muted">Manage your plan, usage, and payment methods</p>
        <a
          href="#"
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-transparent text-text-secondary border border-border-default hover:bg-bg-surface-hover hover:text-text-primary transition-all no-underline"
        >
          <HelpCircle className="w-4 h-4" />
          Support
        </a>
      </div>

      {/* Content */}
      <div className="p-6 max-w-[1200px]">
        {/* Current Plan Hero */}
        <PlanHeroCard plan={mockCurrentPlan} metrics={mockPlanMetrics} />

        {/* Usage */}
        <UsageMeters usage={mockUsageData} resetDate="March 1, 2026" />

        {/* Payment Method */}
        <PaymentMethod paymentMethod={mockPaymentMethod} />

        {/* Invoice History */}
        <InvoiceTable invoices={mockInvoices} />

        {/* Plan Options */}
        <PlanComparison plans={mockAvailablePlans} />

        {/* Upgrade CTA */}
        <UpgradeCTA />
      </div>
    </AppShell>
  );
}
