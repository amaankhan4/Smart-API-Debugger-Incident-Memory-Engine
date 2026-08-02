import { useState } from 'react';

type NotesPanelProps = {
  title?: string;
  notes: { id: string; note: string; createdAt: string }[];
  onAddNote: (value: string) => Promise<void>;
};

export const NotesPanel = ({ title = 'Notes', notes, onAddNote }: NotesPanelProps) => {
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  return (
    <section className="card p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-200">🧠 {title}</h3>
      <div className="space-y-2">
        {notes.map((note) => (
          <div key={note.id} className="rounded-lg border border-slate-700/70 bg-slate-900/80 p-3">
            <p className="whitespace-pre-wrap text-sm text-slate-200">{note.note}</p>
            <p className="mt-1 text-xs text-slate-500">{new Date(note.createdAt).toLocaleString()}</p>
          </div>
        ))}
        {notes.length === 0 && <p className="text-xs text-slate-500">No notes yet.</p>}
      </div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={3}
        className="input mt-3"
        placeholder="Write debugging notes..."
      />
      <button
        className="button mt-3"
        disabled={!draft.trim() || saving}
        onClick={async () => {
          setSaving(true);
          await onAddNote(draft.trim());
          setDraft('');
          setSaving(false);
        }}
      >
        {saving ? 'Saving...' : 'Add note'}
      </button>
    </section>
  );
};
