'use client';

import { AlertTriangle, Upload, Trash2 } from 'lucide-react';

export function DangerZone() {
  return (
    <div className="bg-[rgba(239,68,68,0.05)] border border-[rgba(239,68,68,0.2)] rounded-xl p-6">
      <h3 className="text-base font-semibold text-status-error mb-4 flex items-center gap-2.5">
        <AlertTriangle className="w-5 h-5" />
        Danger Zone
      </h3>
      <div className="flex gap-3">
        <button className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-[rgba(239,68,68,0.1)] text-status-error border border-[rgba(239,68,68,0.3)] hover:bg-[rgba(239,68,68,0.2)] transition-all">
          <Upload className="w-4 h-4" />
          Export All Data
        </button>
        <button className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-[rgba(239,68,68,0.1)] text-status-error border border-[rgba(239,68,68,0.3)] hover:bg-[rgba(239,68,68,0.2)] transition-all">
          <Trash2 className="w-4 h-4" />
          Delete Account
        </button>
      </div>
    </div>
  );
}

export default DangerZone;
