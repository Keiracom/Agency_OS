'use client';

import { FileText, Check, Clock, Download } from 'lucide-react';
import { Invoice } from '@/data/mock-billing';

interface InvoiceTableProps {
  invoices: Invoice[];
}

export function InvoiceTable({ invoices }: InvoiceTableProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-2xl mb-6 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <FileText className="w-5 h-5 text-accent-primary" />
          Invoice History
        </div>
        <a href="#" className="text-accent-primary text-sm font-medium hover:underline">
          Download all
        </a>
      </div>

      {/* Table */}
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider bg-bg-surface-hover border-b border-border-subtle">
              Date
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider bg-bg-surface-hover border-b border-border-subtle">
              Description
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider bg-bg-surface-hover border-b border-border-subtle">
              Amount
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider bg-bg-surface-hover border-b border-border-subtle">
              Status
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider bg-bg-surface-hover border-b border-border-subtle"></th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.id} className="hover:bg-bg-surface-hover transition-colors">
              <td className="px-6 py-[18px] text-sm border-b border-border-subtle font-mono text-text-primary">
                {invoice.date}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-border-subtle text-text-secondary">
                {invoice.description}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-border-subtle font-mono font-semibold text-text-primary">
                ${invoice.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-border-subtle">
                {invoice.status === 'paid' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-[5px] rounded-full text-xs font-medium bg-[rgba(34,197,94,0.15)] text-status-success">
                    <Check className="w-3 h-3" />
                    Paid
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-[5px] rounded-full text-xs font-medium bg-[rgba(245,158,11,0.15)] text-status-warning">
                    <Clock className="w-3 h-3" />
                    Pending
                  </span>
                )}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-border-subtle">
                <a href="#" className="text-accent-primary text-sm font-medium hover:underline flex items-center gap-1">
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default InvoiceTable;
