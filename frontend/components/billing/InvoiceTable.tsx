'use client';

import { FileText, Check, Clock, Download } from 'lucide-react';
import { Invoice } from '@/data/mock-billing';

interface InvoiceTableProps {
  invoices: Invoice[];
}

export function InvoiceTable({ invoices }: InvoiceTableProps) {
  return (
    <div className="bg-bg-panel border border-rule rounded-2xl mb-6 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-ink font-semibold">
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
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-ink-3 uppercase tracking-wider bg-bg-panel-hover border-b border-rule">
              Date
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-ink-3 uppercase tracking-wider bg-bg-panel-hover border-b border-rule">
              Description
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-ink-3 uppercase tracking-wider bg-bg-panel-hover border-b border-rule">
              Amount
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-ink-3 uppercase tracking-wider bg-bg-panel-hover border-b border-rule">
              Status
            </th>
            <th className="text-left px-6 py-3.5 text-[11px] font-semibold text-ink-3 uppercase tracking-wider bg-bg-panel-hover border-b border-rule"></th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.id} className="hover:bg-bg-panel-hover transition-colors">
              <td className="px-6 py-[18px] text-sm border-b border-rule font-mono text-ink">
                {invoice.date}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-rule text-ink-2">
                {invoice.description}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-rule font-mono font-semibold text-ink">
                ${invoice.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </td>
              <td className="px-6 py-[18px] text-sm border-b border-rule">
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
              <td className="px-6 py-[18px] text-sm border-b border-rule">
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
