import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEventContext, getSimilarEvents } from 'api/events';
import type { EventRecord } from 'types/api';
import { formatDate } from 'utils/format';
import { NotesPanel } from './NotesPanel';

type Props = {
  event: EventRecord | null;
  onClose: () => void;
};

export const EventDetailDrawer = ({ event, onClose }: Props) => {
  const storageKey = useMemo(() => (event ? `event-notes:${event.id}` : ''), [event]);
  const [localNotes, setLocalNotes] = useState<{ id: string; note: string; createdAt: string }[]>([]);

  useEffect(() => {
    if (!storageKey) return;
    setLocalNotes(JSON.parse(localStorage.getItem(storageKey) ?? '[]'));
  }, [storageKey]);

  const { data: context } = useQuery({
    queryKey: ['event-context', event?.id],
    queryFn: () => getEventContext(event!.id),
    enabled: Boolean(event)
  });

  const { data: similar } = useQuery({
    queryKey: ['event-similar', event?.id],
    queryFn: () => getSimilarEvents(event?.message ?? '', 8),
    enabled: Boolean(event?.message)
  });

  if (!event) return null;

  return (
    <aside className="fixed inset-y-0 right-0 z-20 w-full max-w-2xl border-l border-slate-800 bg-slate-950/95 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Event detail</h2>
          <p className="text-xs text-slate-500">{event.id}</p>
        </div>
        <button className="rounded-md border border-slate-700 px-2 py-1 text-xs" onClick={onClose}>
          Close
        </button>
      </div>

      <div className="space-y-4 overflow-y-auto pb-10">
        <section className="card p-4">
          <h3 className="text-sm font-semibold">Event Info</h3>
          <p className="mt-2 text-sm text-slate-200">{event.message}</p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-400">
            <span>Level: {event.level}</span>
            <span>Service: {event.service ?? 'unknown'}</span>
            <span>Timestamp: {formatDate(event.timestamp)}</span>
            <span>File: {event.file_id}</span>
          </div>
        </section>

        <section className="card p-4">
          <h3 className="text-sm font-semibold">🔍 Similar Events</h3>
          <div className="mt-2 space-y-2">
            {similar?.matches.map((match) => (
              <div key={match.vector_id} className="rounded-md border border-slate-700 bg-slate-900 p-2">
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>{match.event.level}</span>
                  <span>distance: {match.distance?.toFixed(4) ?? 'n/a'}</span>
                </div>
                <p className="text-sm text-slate-200">{match.event.message}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="card p-4">
          <h3 className="text-sm font-semibold">📜 Surrounding Logs</h3>
          <div className="mt-2 max-h-56 space-y-2 overflow-y-auto rounded-md bg-slate-900 p-2">
            {context?.line_window.map((line) => (
              <p key={line.id} className="text-xs text-slate-300">
                <span className="mr-2 text-slate-500">#{line.line_no}</span>
                {line.message}
              </p>
            ))}
            {context?.line_window.length === 0 && <p className="text-xs text-slate-500">No context available</p>}
          </div>
        </section>

        <NotesPanel
          title="Event Notes (stored locally)"
          notes={localNotes}
          onAddNote={async (note) => {
            const saved = JSON.parse(localStorage.getItem(storageKey) ?? '[]');
            const updated = [{ id: crypto.randomUUID(), note, createdAt: new Date().toISOString() }, ...saved];
            localStorage.setItem(storageKey, JSON.stringify(updated));
            setLocalNotes(updated);
          }}
        />
      </div>
    </aside>
  );
};
