import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  Database,
  FileText,
  Inbox,
  ShieldAlert,
  Upload
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { errorMessage } from 'api/client';
import { getEvents } from 'api/events';
import { getFiles } from 'api/files';
import { getIncidents } from 'api/incidents';
import { getAnalytics } from 'api/search';
import { ErrorTrendChart } from 'components/Charts';
import { PageHeader } from 'components/PageHeader';
import { StatCard } from 'components/StatCard';
import {
  FileStatusBadge,
  LevelBadge,
  ServiceBadge,
  SeverityBadge
} from 'components/ui/Badges';
import { CardSkeleton, ChartSkeleton, EmptyState, ErrorState, TableSkeleton } from 'components/ui/States';
import { bytesToReadable, formatNumber, formatPercent, formatRelative } from 'utils/format';

export const OverviewPage = () => {
  const analytics = useQuery({ queryKey: ['analytics', 14], queryFn: () => getAnalytics(14) });
  const files = useQuery({ queryKey: ['files', 'recent'], queryFn: () => getFiles({ limit: 5 }) });
  const incidents = useQuery({
    queryKey: ['incidents', 'recent'],
    queryFn: () => getIncidents({ limit: 5, sort: 'last_seen' })
  });
  const criticalEvents = useQuery({
    queryKey: ['events', 'recent-errors'],
    queryFn: () => getEvents({ only_errors: true, limit: 6 })
  });

  const overview = analytics.data?.overview;
  const errorTrend = analytics.data?.error_trend ?? [];
  const hasData = (overview?.total_events ?? 0) > 0;

  return (
    <div className="mx-auto max-w-[1600px]">
      <PageHeader
        title="Overview"
        description="Live health of every log file, event and incident you own."
        actions={
          <Link to="/files?upload=1" className="btn-primary">
            <Upload size={14} />
            Upload logs
          </Link>
        }
      />

      {analytics.isLoading ? (
        <CardSkeleton />
      ) : analytics.isError ? (
        <div className="panel">
          <ErrorState message={errorMessage(analytics.error)} onRetry={() => analytics.refetch()} />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Files"
            value={formatNumber(overview?.total_files)}
            hint="Uploaded log files"
            icon={FileText}
            to="/files"
          />
          <StatCard
            label="Events"
            value={formatNumber(overview?.total_events)}
            hint={`${formatNumber(overview?.events_pending_embedding)} awaiting embedding`}
            icon={Database}
            to="/logs"
          />
          <StatCard
            label="Errors"
            value={formatNumber(overview?.total_errors)}
            hint={`${formatPercent(overview?.error_rate ?? 0)} of all events`}
            icon={AlertTriangle}
            tone="critical"
            to="/logs?only_errors=1"
          />
          <StatCard
            label="Open incidents"
            value={formatNumber(overview?.open_incidents)}
            hint={`${formatNumber(overview?.resolved_incidents)} resolved`}
            icon={ShieldAlert}
            tone="warning"
            to="/incidents"
          />
        </div>
      )}

      <section className="panel mt-4 p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold">Error trend</h2>
            <p className="mt-0.5 text-xs text-content-muted">Events and errors over the last 14 days</p>
          </div>
        </div>
        {analytics.isLoading ? (
          <ChartSkeleton />
        ) : !hasData || errorTrend.length === 0 ? (
          <EmptyState
            icon={<Inbox size={18} />}
            title="No events yet"
            description="Upload and ingest a log file to start building your error history."
            action={
              <Link to="/files?upload=1" className="btn-primary">
                <Upload size={14} />
                Upload a log file
              </Link>
            }
          />
        ) : (
          <ErrorTrendChart data={errorTrend} />
        )}
      </section>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <section className="panel">
          <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
            <h2 className="text-sm font-semibold">Recent files</h2>
            <Link to="/files" className="text-xs text-accent-soft hover:underline">
              View all
            </Link>
          </header>
          {files.isLoading ? (
            <TableSkeleton rows={4} columns={3} />
          ) : files.isError ? (
            <ErrorState message={errorMessage(files.error)} onRetry={() => files.refetch()} />
          ) : files.data?.items.length === 0 ? (
            <EmptyState
              icon={<FileText size={18} />}
              title="No files uploaded"
              description="Drop a .log or .txt file to begin."
              action={
                <Link to="/files?upload=1" className="btn-secondary">
                  Upload
                </Link>
              }
            />
          ) : (
            <ul className="divide-y divide-line">
              {files.data?.items.map((file) => (
                <li key={file.file_id}>
                  <Link
                    to="/files"
                    className="flex items-center justify-between gap-3 px-5 py-3 transition-colors hover:bg-surface-hover"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-mono text-xs text-content">{file.filename}</div>
                      <div className="mt-1 text-2xs text-content-subtle">
                        {bytesToReadable(file.size_bytes)} · {formatRelative(file.uploaded_at)}
                      </div>
                    </div>
                    <FileStatusBadge status={file.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
            <h2 className="text-sm font-semibold">Recent incidents</h2>
            <Link to="/incidents" className="text-xs text-accent-soft hover:underline">
              View all
            </Link>
          </header>
          {incidents.isLoading ? (
            <TableSkeleton rows={4} columns={3} />
          ) : incidents.isError ? (
            <ErrorState message={errorMessage(incidents.error)} onRetry={() => incidents.refetch()} />
          ) : incidents.data?.items.length === 0 ? (
            <EmptyState
              icon={<ShieldAlert size={18} />}
              title="No incidents yet"
              description="Incidents appear automatically once enough similar errors have been embedded and clustered."
            />
          ) : (
            <ul className="divide-y divide-line">
              {incidents.data?.items.map((incident) => (
                <li key={incident.id}>
                  <Link
                    to={`/incidents/${incident.id}`}
                    className="flex items-start justify-between gap-3 px-5 py-3 transition-colors hover:bg-surface-hover"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-xs text-content">{incident.title}</div>
                      <div className="mt-1 text-2xs text-content-subtle">
                        {incident.event_count} events · {formatRelative(incident.last_seen)}
                      </div>
                    </div>
                    <SeverityBadge severity={incident.severity} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
            <h2 className="text-sm font-semibold">Recent critical errors</h2>
            <Link to="/logs?only_errors=1" className="text-xs text-accent-soft hover:underline">
              View all
            </Link>
          </header>
          {criticalEvents.isLoading ? (
            <TableSkeleton rows={4} columns={3} />
          ) : criticalEvents.isError ? (
            <ErrorState
              message={errorMessage(criticalEvents.error)}
              onRetry={() => criticalEvents.refetch()}
            />
          ) : criticalEvents.data?.items.length === 0 ? (
            <EmptyState
              icon={<AlertTriangle size={18} />}
              title="No errors recorded"
              description="Nothing has failed in your ingested logs yet."
            />
          ) : (
            <ul className="divide-y divide-line">
              {criticalEvents.data?.items.map((event) => (
                <li key={event.id}>
                  <Link
                    to={`/logs?event=${event.id}`}
                    className="block px-5 py-3 transition-colors hover:bg-surface-hover"
                  >
                    <div className="flex items-center gap-2">
                      <LevelBadge level={event.level} />
                      <ServiceBadge service={event.service} />
                    </div>
                    <p className="mt-1.5 truncate font-mono text-2xs text-content-muted">
                      {event.message}
                    </p>
                    <div className="mt-1 text-2xs text-content-subtle">
                      {formatRelative(event.timestamp)}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
};
