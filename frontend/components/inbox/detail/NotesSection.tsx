/**
 * FILE: frontend/components/inbox/detail/NotesSection.tsx
 * PURPOSE: Notes with add button
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { Note } from '@/lib/mock/inbox-data';
import { Edit3, Plus } from 'lucide-react';

interface NotesSectionProps {
  notes: Note[];
  onAddNote?: () => void;
}

export function NotesSection({ notes, onAddNote }: NotesSectionProps) {
  return (
    <div className="bg-bg-base rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-text-muted">
        <Edit3 className="w-3.5 h-3.5" />
        Notes
      </div>
      <div className="space-y-2.5">
        {notes.map((note) => (
          <div
            key={note.id}
            className="bg-amber-500/8 border-l-[3px] border-l-amber-500 rounded-r-lg p-3"
          >
            <p className="text-[10px] text-text-muted mb-1.5">{note.timestamp}</p>
            <p className="text-[13px] text-text-secondary leading-relaxed">{note.text}</p>
          </div>
        ))}
        
        <button
          onClick={onAddNote}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2.5 border border-dashed border-border-default rounded-lg text-xs text-text-muted hover:text-text-secondary hover:border-border-strong hover:bg-white/[0.03] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Note
        </button>
      </div>
    </div>
  );
}
