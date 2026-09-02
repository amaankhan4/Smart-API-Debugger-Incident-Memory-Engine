import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, NotebookPen, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { errorMessage } from 'api/client';
import { addIncidentNote, deleteIncidentNote, getIncidentNotes } from 'api/incidents';
import { EmptyState, ErrorState, Skeleton } from 'components/ui/States';
import type { NoteType } from 'types/api';
import { formatRelative, titleCase } from 'utils/format';

const NOTE_TYPES: NoteType[] = ['investigation', 'root_cause', 'fix', 'follow_up', 'general'];

const TYPE_STYLES: Record<NoteType, string> = {
  investigation: 'border-accent/30 bg-accent-dim text-accent-soft',
  root_cause: 'border-severity-critical/40 bg-severity-critical/10 text-severity-critical',
  fix: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  follow_up: 'border-severity-medium/40 bg-severity-medium/10 text-severity-medium',
  general: 'border-line-strong bg-surface-hover text-content-muted'
};

export const NotesPanel = ({
  incidentId,
  eventId
}: {
  incidentId: string;
  eventId?: string;
}) => {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState('');
  const [noteType, setNoteType] = useState<NoteType>('investigation');

  const notesQuery = useQuery({
    queryKey: ['incident-notes', incidentId],
    queryFn: () => getIncidentNotes(incidentId)
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['incident-notes', incidentId] });

  const addMutation = useMutation({
    mutationFn: () =>
      addIncidentNote(incidentId, { note: draft.trim(), type: noteType, event_id: eventId }),
    onSuccess: () => {
      setDraft('');
      toast.success('Note saved to incident memory');
      invalidate();
    },
    onError: (error) => toast.error(errorMessage(error, 'Could not save the note'))
  });

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) => deleteIncidentNote(incidentId, noteId),
    onSuccess: () => {
      toast.success('Note deleted');
      invalidate();
    },
    onError: (error) => toast.error(errorMessage(error, 'Could not delete the note'))
  });

  const notes = notesQuery.data?.items ?? [];

  return (
    <section className="panel">
      <header className="border-b border-line px-5 py-3.5">
        <h2 className="text-sm font-semibold">Investigation notes</h2>
        <p className="mt-0.5 text-xs text-content-muted">
          What you learn here becomes searchable knowledge for whoever hits this next.
        </p>
      </header>

      <div className="border-b border-line p-4">
        <label htmlFor="note-draft" className="sr-only">
          Note
        </label>
        <textarea
          id="note-draft"
          rows={3}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Root cause: retry storm exhausted the database connection pool…"
          className="input resize-y font-sans"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1.5">
            {NOTE_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setNoteType(type)}
                aria-pressed={noteType === type}
                className={`chip transition-colors ${
                  noteType === type ? TYPE_STYLES[type] : 'border-line bg-surface-raised text-content-subtle'
                }`}
              >
                {titleCase(type)}
              </button>
            ))}
          </div>
          <button
            type="button"
            disabled={!draft.trim() || addMutation.isPending}
            onClick={() => addMutation.mutate()}
            className="btn-primary"
          >
            {addMutation.isPending ? (
              <Loader2 size={13} className="animate-spin" aria-hidden />
            ) : (
              <NotebookPen size={13} aria-hidden />
            )}
            Add note
          </button>
        </div>
      </div>

      {notesQuery.isLoading ? (
        <div className="space-y-3 p-5">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : notesQuery.isError ? (
        <ErrorState message={errorMessage(notesQuery.error)} onRetry={() => notesQuery.refetch()} />
      ) : notes.length === 0 ? (
        <EmptyState
          icon={<NotebookPen size={18} />}
          title="No notes yet"
          description="Record what you checked, what you suspect and how it was fixed."
        />
      ) : (
        <ul className="divide-y divide-line">
          {notes.map((note) => (
            <li key={note.id} className="px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`chip ${TYPE_STYLES[note.type]}`}>{titleCase(note.type)}</span>
                  <span className="text-2xs text-content-subtle">
                    {note.author_name ?? 'Unknown'} · {formatRelative(note.created_at)}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(note.id)}
                  className="btn-ghost shrink-0 p-1"
                  aria-label="Delete note"
                  title="Delete note"
                >
                  <Trash2 size={13} />
                </button>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-content">{note.note}</p>
              {note.event_id && (
                <p className="mt-1.5 font-mono text-2xs text-content-subtle">
                  linked event: {note.event_id}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

