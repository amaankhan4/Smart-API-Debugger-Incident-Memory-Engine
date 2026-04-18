import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { addIncidentNote, getIncidentDetail } from 'api/incidents';
import { NotesPanel } from 'components/NotesPanel';
import { formatDate } from 'utils/format';

export const IncidentDetailPage = () => {
  const { incidentId = '' } = useParams();
  const [status, setStatus] = useState<'open' | 'resolved'>('open');
  const storageKey = useMemo(() => `incident-notes-local:${incidentId}`, [incidentId]);
  const [localNotes, setLocalNotes] = useState<{ id: string; note: string; createdAt: string }[]>(
    JSON.parse(localStorage.getItem(storageKey) ?? '[]')
  );

  const incidentQuery = useQuery({
    queryKey: ['incident-detail', incidentId],
    queryFn: () => getIncidentDetail(incidentId),
    enabled: Boolean(incidentId)
  });

  const noteMutation = useMutation({
    mutationFn: (note: string) => addIncidentNote(incidentId, note)
  });

  const incident = incidentQuery.data?.incident;

  return (
    <section className="space-y-4">
      <div className="card p-4">
        <h1 className="text-lg font-semibold">{incident?.title ?? incident?.cluster_key ?? incidentId}</h1>
        <p className="mt-1 text-xs text-slate-500">Severity: {incident?.severity ?? 'N/A'}</p>
        <div className="mt-3 flex items-center gap-2 text-xs">
          <span className="text-slate-400">Status</span>
          <select className="input max-w-40" value={status} onChange={(e) => setStatus(e.target.value as 'open' | 'resolved')}>
            <option value="open">open</option>
            <option value="resolved">resolved</option>
          </select>
          <span className="text-slate-500">(local UI state)</span>
        </div>
      </div>

      <div className="card p-4">
        <h2 className="text-sm font-semibold">Timeline</h2>
        <div className="mt-3 space-y-2">
          {(incidentQuery.data?.events ?? []).map((event) => (
            <div key={event.id} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
              <p className="text-sm text-slate-200">{event.message}</p>
              <p className="mt-1 text-xs text-slate-500">{event.level} • {event.service} • {formatDate(event.timestamp)}</p>
            </div>
          ))}
        </div>
      </div>

      <NotesPanel
        title="Incident Notes"
        notes={localNotes}
        onAddNote={async (note) => {
          await noteMutation.mutateAsync(note);
          const updated = [{ id: crypto.randomUUID(), note, createdAt: new Date().toISOString() }, ...localNotes];
          setLocalNotes(updated);
          localStorage.setItem(storageKey, JSON.stringify(updated));
        }}
      />
    </section>
  );
};
