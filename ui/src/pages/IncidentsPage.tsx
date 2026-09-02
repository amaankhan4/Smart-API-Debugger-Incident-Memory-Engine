import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, RotateCcw, ShieldAlert, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { errorMessage } from 'api/client';
import { getIncidents, runClustering, type IncidentFilters } from 'api/incidents';
import { PageHeader } from 'components/PageHeader';
import { IncidentStatusBadge, ServiceBadge, SeverityBadge } from 'components/ui/Badges';
import { EmptyState, ErrorState, TableSkeleton } from 'components/ui/States';
import type { IncidentSeverity, IncidentStatus } from 'types/api';
import { formatDate, formatNumber, formatRelative } from 'utils/format';

const STATUSES: IncidentStatus[] = ['open', 'investigating', 'resolved', 'ignored'];
const SEVERITIES: IncidentSeverity[] = ['critical', 'high', 'medium', 'low'];
const PAGE_SIZE = 25;

export const IncidentsPage = () => {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<IncidentFilters>({
    sort: 'last_seen',
    order: 'desc',
    limit: PAGE_SIZE,
    offset: 0
  });

  const incidentsQuery = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => getIncidents(filters)
  });

  const clusterMutation = useMutation({
    mutationFn: runClustering,
    onSuccess: (result) => {
      if (result.reason === 'not_enough_events' || result.reason === 'not_enough_embeddings') {
        toast.info('Not enough embedded error events to form incidents yet.');
      } else {
        toast.success(
          `${result.clusters_created} new, ${result.clusters_updated} updated across ${formatNumber(result.events_clustered)} events`
        );
      }
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (error) => toast.error(errorMessage(error, 'Clustering failed'))
  });

  const items = incidentsQuery.data?.items ?? [];
  const total = incidentsQuery.data?.total ?? 0;
  const hasFilters = Boolean(filters.status || filters.severity || filters.search);

  const patch = (next: Partial<IncidentFilters>) =>
    setFilters((current) => ({ ...current, ...next, offset: 0 }));

  return (
    <div className="mx-auto max-w-[1600px]">
      <PageHeader
        title="Incidents"
        description="Recurring failures grouped by semantic similarity. Treat each as a candidate, not a confirmed root cause."
        actions={
          <button
            type="button"
            onClick={() => clusterMutation.mutate()}
            disabled={clusterMutation.isPending}
            className="btn-secondary"
          >
            {clusterMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" aria-hidden />
            ) : (
              <Sparkles size={14} aria-hidden />
            )}
            Run clustering
          </button>
        }
      />

      <div className="panel mb-4 flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-[200px] flex-1">
          <label htmlFor="incident-search" className="mb-1.5 block text-xs font-medium text-content-muted">
            Title contains
          </label>
          <input
            id="incident-search"
            value={filters.search ?? ''}
            onChange={(event) => patch({ search: event.target.value || undefined })}
            placeholder="database timeout"
            className="input"
          />
        </div>

        <div>
          <label htmlFor="incident-status" className="mb-1.5 block text-xs font-medium text-content-muted">
            Status
          </label>
          <select
            id="incident-status"
            value={filters.status ?? ''}
            onChange={(event) =>
              patch({ status: (event.target.value || undefined) as IncidentStatus | undefined })
            }
            className="input w-40"
          >
            <option value="">All statuses</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="incident-severity" className="mb-1.5 block text-xs font-medium text-content-muted">
            Severity
          </label>
          <select
            id="incident-severity"
            value={filters.severity ?? ''}
            onChange={(event) =>
              patch({ severity: (event.target.value || undefined) as IncidentSeverity | undefined })
            }
            className="input w-40"
          >
            <option value="">All severities</option>
            {SEVERITIES.map((severity) => (
              <option key={severity} value={severity}>
                {severity}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="incident-sort" className="mb-1.5 block text-xs font-medium text-content-muted">
            Sort by
          </label>
          <select
            id="incident-sort"
            value={filters.sort}
            onChange={(event) => patch({ sort: event.target.value as IncidentFilters['sort'] })}
            className="input w-40"
          >
            <option value="last_seen">Last seen</option>
            <option value="first_seen">First seen</option>
            <option value="event_count">Event count</option>
            <option value="created_at">Created</option>
          </select>
        </div>

        {hasFilters && (
          <button
            type="button"
            onClick={() =>
              setFilters({ sort: 'last_seen', order: 'desc', limit: PAGE_SIZE, offset: 0 })
            }
            className="btn-ghost mb-1 px-2 py-1 text-xs"
          >
            <RotateCcw size={12} />
            Clear
          </button>
        )}
      </div>

      <section className="panel">
        {incidentsQuery.isLoading ? (
          <TableSkeleton rows={8} columns={6} />
        ) : incidentsQuery.isError ? (
          <ErrorState
            message={errorMessage(incidentsQuery.error)}
            onRetry={() => incidentsQuery.refetch()}
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<ShieldAlert size={18} />}
            title={hasFilters ? 'No incidents match these filters' : 'No incidents yet'}
            description={
              hasFilters
                ? 'Try clearing the status or severity filter.'
                : 'Upload and ingest a log file to start discovering recurring failures. Incidents form once similar errors have been embedded and clustered.'
            }
            action={
              hasFilters ? (
                <button
                  type="button"
                  onClick={() =>
                    setFilters({ sort: 'last_seen', order: 'desc', limit: PAGE_SIZE, offset: 0 })
                  }
                  className="btn-secondary"
                >
                  Clear filters
                </button>
              ) : (
                <Link to="/files?upload=1" className="btn-primary">
                  Upload a log file
                </Link>
              )
            }
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line text-2xs uppercase tracking-wide text-content-subtle">
                  <tr>
                    <th scope="col" className="px-5 py-2.5 font-medium">Severity</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Incident</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Services</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Events</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">First seen</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Last seen</th>
                    <th scope="col" className="px-5 py-2.5 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {items.map((incident) => (
                    <tr key={incident.id} className="transition-colors hover:bg-surface-hover">
                      <td className="px-5 py-3">
                        <SeverityBadge severity={incident.severity} />
                      </td>
                      <td className="max-w-[380px] px-3 py-3">
                        <Link
                          to={`/incidents/${incident.id}`}
                          className="block truncate text-xs text-content hover:text-accent-soft"
                          title={incident.title}
                        >
                          {incident.title}
                        </Link>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          {incident.services.slice(0, 2).map((service) => (
                            <ServiceBadge key={service} service={service} />
                          ))}
                          {incident.services.length > 2 && (
                            <span className="text-2xs text-content-subtle">
                              +{incident.services.length - 2}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-xs tabular-nums text-content-muted">
                        {formatNumber(incident.event_count)}
                      </td>
                      <td
                        className="whitespace-nowrap px-3 py-3 text-xs text-content-muted"
                        title={formatDate(incident.first_seen)}
                      >
                        {formatRelative(incident.first_seen)}
                      </td>
                      <td
                        className="whitespace-nowrap px-3 py-3 text-xs text-content-muted"
                        title={formatDate(incident.last_seen)}
                      >
                        {formatRelative(incident.last_seen)}
                      </td>
                      <td className="px-5 py-3">
                        <IncidentStatusBadge status={incident.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {total > PAGE_SIZE && (
              <footer className="flex items-center justify-between border-t border-line px-5 py-3 text-xs text-content-muted">
                <span>
                  {(filters.offset ?? 0) + 1}–{(filters.offset ?? 0) + items.length} of{' '}
                  {formatNumber(total)}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={(filters.offset ?? 0) === 0}
                    onClick={() =>
                      setFilters((current) => ({
                        ...current,
                        offset: Math.max(0, (current.offset ?? 0) - PAGE_SIZE)
                      }))
                    }
                    className="btn-secondary px-2 py-1 text-xs"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={(filters.offset ?? 0) + items.length >= total}
                    onClick={() =>
                      setFilters((current) => ({
                        ...current,
                        offset: (current.offset ?? 0) + PAGE_SIZE
                      }))
                    }
                    className="btn-secondary px-2 py-1 text-xs"
                  >
                    Next
                  </button>
                </div>
              </footer>
            )}
          </>
        )}
      </section>
    </div>
  );
};

