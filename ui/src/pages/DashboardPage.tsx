import { useQuery } from '@tanstack/react-query';
import { getFiles } from 'api/files';
import { getEvents } from 'api/events';
import { getIncidents } from 'api/incidents';
import { StatCard } from 'components/StatCard';
import { formatDate } from 'utils/format';

export const DashboardPage = () => {
  const filesQuery = useQuery({ queryKey: ['files'], queryFn: getFiles, refetchInterval: 15000 });
  const eventsQuery = useQuery({ queryKey: ['events-dashboard'], queryFn: () => getEvents({ limit: 200 }), refetchInterval: 15000 });
  const incidentsQuery = useQuery({ queryKey: ['incidents-dashboard'], queryFn: getIncidents, refetchInterval: 15000 });

  const events = eventsQuery.data?.items ?? [];
  const recentErrors = events.filter((event) => event.level === 'ERROR').slice(0, 6);

  return (
    <section className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Files Uploaded" value={filesQuery.data?.length ?? 0} />
        <StatCard label="Events Processed" value={eventsQuery.data?.count ?? 0} />
        <StatCard label="Incidents Detected" value={incidentsQuery.data?.count ?? 0} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card p-4">
          <h2 className="text-sm font-semibold">Recent errors</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[500px] text-left text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="pb-2">Message</th>
                  <th className="pb-2">Service</th>
                  <th className="pb-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {recentErrors.map((event) => (
                  <tr key={event.id} className="border-t border-slate-800">
                    <td className="py-2 text-slate-200">{event.message}</td>
                    <td className="py-2 text-slate-400">{event.service ?? 'unknown'}</td>
                    <td className="py-2 text-slate-500">{formatDate(event.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card p-4">
          <h2 className="text-sm font-semibold">Recent incidents</h2>
          <div className="mt-3 space-y-2">
            {(incidentsQuery.data?.items ?? []).slice(0, 5).map((incident) => (
              <div key={incident.id} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                <p className="text-sm font-medium text-slate-200">{incident.title ?? incident.cluster_key ?? incident.id}</p>
                <p className="text-xs text-slate-400">Severity: {incident.severity ?? 'N/A'}</p>
                <p className="text-xs text-slate-500">Status: {incident.status ?? 'open'}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
};
