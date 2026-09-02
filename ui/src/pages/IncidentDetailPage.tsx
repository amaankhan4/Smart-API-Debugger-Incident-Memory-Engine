import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, Layers, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';

import { errorMessage } from 'api/client';
import { getIncidentDetail, updateIncidentStatus } from 'api/incidents';
import { IncidentTimelineChart } from 'components/Charts';
import { EventCard } from 'components/EventCard';
import { EventDetailDrawer } from 'components/EventDetailDrawer';
import { NotesPanel } from 'components/NotesPanel';
import { PageHeader } from 'components/PageHeader';
import { CategoryBadge, IncidentStatusBadge, ServiceBadge, SeverityBadge } from 'components/ui/Badges';
import { Field } from 'components/ui/Primitives';
import { CardSkeleton, EmptyState, ErrorState } from 'components/ui/States';
import type { EventRecord, IncidentStatus } from 'types/api';
import { formatDate, formatNumber, formatRelative, titleCase } from 'utils/format';

const STATUS_FLOW: IncidentStatus[] = ['open', 'investigating', 'resolved', 'ignored'];

export const IncidentDetailPage = () => {
  const { incidentId = '' } = useParams();
  const queryClient = useQueryClient();
  const [selectedEvent, setSelectedEvent] = useState<EventRecord | null>(null);

  const detailQuery = useQuery({
    queryKey: ['incident-detail', incidentId],
    queryFn: () => getIncidentDetail(incidentId),
    enabled: Boolean(incidentId)
  });

  const statusMutation = useMutation({
    mutationFn: (status: IncidentStatus) => updateIncidentStatus(incidentId, { status }),
    onSuccess: (updated) => {
      toast.success(`Incident marked as ${updated.status}`);
      queryClient.invalidateQueries({ queryKey: ['incident-detail', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (error) => toast.error(errorMessage(error, 'Could not update the status'))
  });

  if (detailQuery.isLoading) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <CardSkeleton count={4} />
      </div>
    );
  }

  if (detailQuery.isError) {
    return (
      <div className="panel mx-auto max-w-[1400px]">
        <ErrorState message={errorMessage(detailQuery.error)} onRetry={() => detailQuery.refetch()} />
      </div>
    );
  }

  const incident = detailQuery.data!.incident;
  const { representative_events: events, timeline, similar_incidents: similar } = detailQuery.data!;

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title={incident.title}
        breadcrumbs={
          <span className="flex items-center gap-1">
            <Link to="/incidents" className="hover:text-content-muted">
              Incidents
            </Link>
            <ChevronRight size={12} aria-hidden />
            <span className="text-content-muted">{incident.cluster_key.slice(0, 12)}</span>
          </span>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {STATUS_FLOW.map((status) => (
              <button
                key={status}
                type="button"
                disabled={statusMutation.isPending || incident.status === status}
                onClick={() => statusMutation.mutate(status)}
                className={
                  incident.status === status ? 'btn-primary text-xs' : 'btn-secondary text-xs'
                }
              >
                {statusMutation.isPending && statusMutation.variables === status && (
                  <Loader2 size={12} className="animate-spin" aria-hidden />
                )}
                {titleCase(status)}
              </button>
            ))}
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <SeverityBadge severity={incident.severity} />
        <IncidentStatusBadge status={incident.status} />
        <CategoryBadge category={incident.error_category} />
        <span className="text-xs text-content-subtle">
          {formatNumber(incident.event_count)} events · first seen{' '}
          {formatRelative(incident.first_seen)} · last seen {formatRelative(incident.last_seen)}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <section className="panel p-5">
            <h2 className="text-sm font-semibold">Activity timeline</h2>
            <p className="mt-0.5 text-xs text-content-muted">
              When events belonging to this incident occurred
            </p>
            <div className="mt-4">
              {timeline.length === 0 ? (
                <EmptyState
                  title="No timeline data"
                  description="Events in this incident have no usable timestamps."
                />
              ) : (
                <IncidentTimelineChart data={timeline} />
              )}
            </div>
          </section>

          <section className="panel">
            <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
              <div>
                <h2 className="text-sm font-semibold">Representative events</h2>
                <p className="mt-0.5 text-xs text-content-muted">
                  The examples closest to the centre of this cluster
                </p>
              </div>
              <Link
                to={`/logs?incident=${incident.id}`}
                className="text-xs text-accent-soft hover:underline"
              >
                View all events
              </Link>
            </header>
            {events.length === 0 ? (
              <EmptyState
                title="No representative events"
                description="Re-run clustering to refresh this incident's examples."
              />
            ) : (
              <div className="space-y-2 p-4">
                {events.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    onClick={() => setSelectedEvent(event)}
                    selected={selectedEvent?.id === event.id}
                  />
                ))}
              </div>
            )}
          </section>

          <NotesPanel incidentId={incident.id} />
        </div>

        <div className="space-y-4">
          <section className="panel p-5">
            <h2 className="mb-2 text-sm font-semibold">Summary</h2>
            <dl>
              <Field label="Incident ID" value={incident.id} mono copyable={incident.id} />
              <Field label="Severity" value={titleCase(incident.severity)} />
              <Field label="Status" value={titleCase(incident.status)} />
              <Field label="Events" value={formatNumber(incident.event_count)} />
              <Field label="First seen" value={formatDate(incident.first_seen)} mono />
              <Field label="Last seen" value={formatDate(incident.last_seen)} mono />
              {incident.resolved_at && (
                <Field label="Resolved" value={formatDate(incident.resolved_at)} mono />
              )}
              <Field label="Cluster key" value={incident.cluster_key.slice(0, 16)} mono />
            </dl>
          </section>

          <section className="panel p-5">
            <h2 className="mb-3 text-sm font-semibold">Affected services</h2>
            {incident.services.length === 0 ? (
              <p className="text-xs text-content-subtle">No service could be identified.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {incident.services.map((service) => (
                  <ServiceBadge key={service} service={service} />
                ))}
              </div>
            )}

            <h2 className="mb-3 mt-5 text-sm font-semibold">Affected endpoints</h2>
            {incident.endpoints.length === 0 ? (
              <p className="text-xs text-content-subtle">No endpoint information in these logs.</p>
            ) : (
              <ul className="space-y-1">
                {incident.endpoints.map((endpoint) => (
                  <li key={endpoint} className="truncate font-mono text-2xs text-content-muted">
                    {endpoint}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <header className="border-b border-line px-5 py-3.5">
              <h2 className="text-sm font-semibold">Similar past incidents</h2>
              <p className="mt-0.5 text-xs text-content-muted">
                Historical failures with a comparable signature
              </p>
            </header>
            {similar.length === 0 ? (
              <EmptyState
                icon={<Layers size={18} />}
                title="No similar incidents"
                description="Nothing comparable has been recorded yet."
              />
            ) : (
              <ul className="divide-y divide-line">
                {similar.map((match) => (
                  <li key={match.incident.id}>
                    <Link
                      to={`/incidents/${match.incident.id}`}
                      className="block px-5 py-3 transition-colors hover:bg-surface-hover"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <SeverityBadge severity={match.incident.severity} />
                        <span className="text-2xs font-medium text-accent-soft">
                          {Math.round(match.score * 100)}% similar
                        </span>
                      </div>
                      <p className="mt-1.5 truncate text-xs text-content">{match.incident.title}</p>
                      <p className="mt-0.5 text-2xs text-content-subtle">
                        {formatRelative(match.incident.last_seen)}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>

      <EventDetailDrawer event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
};

