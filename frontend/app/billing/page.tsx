'use client';

import { HelpCircle } from 'lucide-react';
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
    <div className="min-h-screen bg-bg-void">
      {/* Header */}
      <header className="bg-bg-surface border-b border-border-subtle px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Billing & Subscription</h1>
          <p className="text-sm text-text-muted mt-1">Manage your plan, usage, and payment methods</p>
        </div>
        <div className="flex gap-3">
          <a
            href="#"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-transparent text-text-secondary border border-border-default hover:bg-bg-surface-hover hover:text-text-primary transition-all no-underline"
          >
            <HelpCircle className="w-4 h-4" />
            Support
          </a>
        </div>
      </header>

      {/* Content */}
      <div className="p-8 max-w-[1200px]">
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
    </div>
  );
}
