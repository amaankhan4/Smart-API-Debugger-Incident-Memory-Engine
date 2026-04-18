import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getIncidents } from 'api/incidents';
import { formatDate } from 'utils/format';

export const IncidentsPage = () => {
  const incidentsQuery = useQuery({ queryKey: ['incidents'], queryFn: getIncidents, refetchInterval: 15000 });

  return (
    <section className="space-y-3">
      {(incidentsQuery.data?.items ?? []).map((incident) => (
        <Link key={incident.id} to={`/incidents/${incident.id}`} className="card block p-4 transition hover:border-indigo-400/60">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100">{incident.title ?? incident.cluster_key ?? incident.id}</h3>
            <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{incident.status ?? 'open'}</span>
          </div>
          <p className="text-xs text-slate-400">Severity: {incident.severity ?? 'unknown'} • Events: {incident.event_count ?? incident.event_ids?.length ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">Created: {formatDate(incident.created_at)}</p>
        </Link>
      ))}
    </section>
  );
};
