import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { errorMessage } from 'api/client';
import { getAnalytics } from 'api/search';
import {
  CategoryDonutChart,
  ErrorTrendChart,
  HorizontalCountChart,
  IncidentsOverTimeChart
} from 'components/Charts';
import { PageHeader } from 'components/PageHeader';
import { FileStatusBadge } from 'components/ui/Badges';
import { CardSkeleton, ChartSkeleton, EmptyState, ErrorState } from 'components/ui/States';
import type { FileStatus } from 'types/api';
import { formatNumber } from 'utils/format';

const RANGES = [
  { days: 7, label: '7d' },
  { days: 14, label: '14d' },
  { days: 30, label: '30d' },
  { days: 90, label: '90d' }
];

const Panel = ({
  title,
  description,
  children
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) => (
  <section className="panel p-5">
    <h2 className="text-sm font-semibold">{title}</h2>
    {description && <p className="mt-0.5 text-xs text-content-muted">{description}</p>}
    <div className="mt-4">{children}</div>
  </section>
);

const NoData = ({ label }: { label: string }) => (
  <EmptyState title={`No ${label} yet`} description="Ingest more logs to populate this view." />
);

export const AnalyticsPage = () => {
  const [days, setDays] = useState(14);
  const analytics = useQuery({ queryKey: ['analytics', days], queryFn: () => getAnalytics(days) });

  if (analytics.isLoading) {
    return (
      <div className="mx-auto max-w-[1600px]">
        <CardSkeleton />
        <div className="mt-4 panel p-5">
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  if (analytics.isError) {
    return (
      <div className="panel mx-auto max-w-[1600px]">
        <ErrorState message={errorMessage(analytics.error)} onRetry={() => analytics.refetch()} />
      </div>
    );
  }

  const data = analytics.data!;
  const hasEvents = data.overview.total_events > 0;

  return (
    <div className="mx-auto max-w-[1600px]">
      <PageHeader
        title="Analytics"
        description="Aggregated directly from your ingested events — no sampling, no placeholders."
        actions={
          <div className="flex gap-1" role="group" aria-label="Time range">
            {RANGES.map((range) => (
              <button
                key={range.days}
                type="button"
                onClick={() => setDays(range.days)}
                aria-pressed={days === range.days}
                className={days === range.days ? 'btn-primary text-xs' : 'btn-secondary text-xs'}
              >
                {range.label}
              </button>
            ))}
          </div>
        }
      />

      {!hasEvents ? (
        <div className="panel">
          <EmptyState
            icon={<BarChart3 size={18} />}
            title="Nothing to analyse yet"
            description="Upload and ingest a log file — analytics populate automatically as events are parsed."
            action={
              <Link to="/files?upload=1" className="btn-primary">
                Upload a log file
              </Link>
            }
          />
        </div>
      ) : (
        <div className="space-y-4">
          <Panel
            title="Error trend"
            description={`All events versus errors over the last ${days} days`}
          >
            {data.error_trend.length === 0 ? (
              <NoData label="trend data" />
            ) : (
              <ErrorTrendChart data={data.error_trend} />
            )}
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Errors by service" description="Which services fail most often">
              {data.errors_by_service.length === 0 ? (
                <NoData label="service errors" />
              ) : (
                <HorizontalCountChart data={data.errors_by_service} />
              )}
            </Panel>

            <Panel title="Errors by category" description="How failures break down by cause">
              {data.errors_by_category.length === 0 ? (
                <NoData label="categorised errors" />
              ) : (
                <CategoryDonutChart data={data.errors_by_category} />
              )}
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Incidents over time" description="New incidents discovered per day">
              {data.incidents_over_time.length === 0 ? (
                <NoData label="incidents" />
              ) : (
                <IncidentsOverTimeChart data={data.incidents_over_time} />
              )}
            </Panel>

            <Panel title="Most affected endpoints" description="Endpoints producing the most errors">
              {data.most_affected_endpoints.length === 0 ? (
                <NoData label="endpoint data" />
              ) : (
                <HorizontalCountChart data={data.most_affected_endpoints} />
              )}
            </Panel>
          </div>

          <section className="panel">
            <header className="border-b border-line px-5 py-3.5">
              <h2 className="text-sm font-semibold">Top recurring errors</h2>
              <p className="mt-0.5 text-xs text-content-muted">
                The failures you keep paying for
              </p>
            </header>
            {data.top_recurring_errors.length === 0 ? (
              <NoData label="recurring errors" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-line text-2xs uppercase tracking-wide text-content-subtle">
                    <tr>
                      <th scope="col" className="px-5 py-2.5 font-medium">Signature</th>
                      <th scope="col" className="px-3 py-2.5 font-medium">Service</th>
                      <th scope="col" className="px-3 py-2.5 font-medium">Category</th>
                      <th scope="col" className="px-3 py-2.5 font-medium">Occurrences</th>
                      <th scope="col" className="px-5 py-2.5 font-medium">Incident</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.top_recurring_errors.map((error) => (
                      <tr
                        key={`${error.signature}-${error.service}`}
                        className="transition-colors hover:bg-surface-hover"
                      >
                        <td className="max-w-[320px] px-5 py-3">
                          <div className="truncate font-mono text-xs text-content">
                            {error.signature}
                          </div>
                          <div className="mt-0.5 truncate text-2xs text-content-subtle">
                            {error.message}
                          </div>
                        </td>
                        <td className="px-3 py-3 font-mono text-xs text-content-muted">
                          {error.service}
                        </td>
                        <td className="px-3 py-3 text-xs text-content-muted">
                          {error.error_category}
                        </td>
                        <td className="px-3 py-3 text-xs tabular-nums text-content-muted">
                          {formatNumber(error.count)}
                        </td>
                        <td className="px-5 py-3 text-xs">
                          {error.incident_id ? (
                            <Link
                              to={`/incidents/${error.incident_id}`}
                              className="text-accent-soft hover:underline"
                            >
                              View incident
                            </Link>
                          ) : (
                            <span className="text-content-subtle">Not clustered</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <Panel title="Processing status" description="Where your uploaded files are in the pipeline">
            {data.processing_status.length === 0 ? (
              <NoData label="files" />
            ) : (
              <ul className="flex flex-wrap gap-3">
                {data.processing_status.map((row) => (
                  <li
                    key={row.status}
                    className="flex items-center gap-2 rounded-lg border border-line bg-surface-raised px-3 py-2"
                  >
                    <FileStatusBadge status={row.status as FileStatus} />
                    <span className="text-sm font-medium tabular-nums">{formatNumber(row.count)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
};
