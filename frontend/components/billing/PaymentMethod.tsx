'use client';

import { CreditCard } from 'lucide-react';
import { PaymentMethod as PaymentMethodType } from '@/data/mock-billing';

interface PaymentMethodProps {
  paymentMethod: PaymentMethodType;
}

export function PaymentMethod({ paymentMethod }: PaymentMethodProps) {
  return (
    <div className="bg-bg-panel border border-rule rounded-2xl mb-6 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-ink font-semibold">
          <CreditCard className="w-5 h-5 text-accent-primary" />
          Payment Method
        </div>
        <a href="#" className="text-accent-primary text-sm font-medium hover:underline">
          Add new
        </a>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="flex items-center justify-between p-5 bg-bg-panel-hover rounded-xl">
          <div className="flex items-center gap-4">
            <div className="w-14 h-9 bg-bg-elevated rounded-md flex items-center justify-center border border-rule-strong">
              {/* Mastercard Logo SVG */}
              <svg viewBox="0 0 32 20" fill="none" className="w-8 h-5">
                <rect width="32" height="20" rx="2" fill="#1A1F71" />
                <circle cx="12" cy="10" r="6" fill="#EB001B" />
                <circle cx="20" cy="10" r="6" fill="#F79E1B" />
                <path d="M16 5.3a6 6 0 010 9.4 6 6 0 000-9.4z" fill="#FF5F00" />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-ink">
                {paymentMethod.type.charAt(0).toUpperCase() + paymentMethod.type.slice(1)} ending in {paymentMethod.lastFour}
              </h4>
              <p className="text-sm text-ink-3 font-mono mt-0.5">
                Expires {paymentMethod.expiryMonth}/{paymentMethod.expiryYear}
              </p>
            </div>
          </div>
          <button className="px-4 py-2 text-sm font-medium rounded-lg bg-transparent text-ink-2 border border-rule-strong hover:bg-bg-panel-hover hover:text-ink transition-all">
            Update
          </button>
        </div>
      </div>
    </div>
  );
}

export default PaymentMethod;
