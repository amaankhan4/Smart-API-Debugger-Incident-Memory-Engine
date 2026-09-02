import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';
import { ExternalLink, ShieldAlert } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { errorMessage } from 'api/client';
import { getEventContext, getSimilarEvents } from 'api/events';
import { NotesPanel } from 'components/NotesPanel';
import { CategoryBadge, LevelBadge, ServiceBadge, StatusCodeBadge } from 'components/ui/Badges';
import { Drawer } from 'components/ui/Drawer';
import { CopyButton, Expandable, Field } from 'components/ui/Primitives';
import { EmptyState, ErrorState, Skeleton } from 'components/ui/States';
import type { EventRecord } from 'types/api';
import { formatDate, formatRelative, titleCase } from 'utils/format';

type TabId = 'context' | 'similar' | 'notes' | 'raw';

const TABS: { id: TabId; label: string }[] = [
  { id: 'context', label: 'Context' },
  { id: 'similar', label: 'Similar events' },
  { id: 'notes', label: 'Notes' },
  { id: 'raw', label: 'Raw log' }
];

const ContextLine = ({ event, highlighted }: { event: EventRecord; highlighted?: boolean }) => (
  <div
    className={clsx(
      'flex gap-3 border-l-2 px-3 py-1.5 font-mono text-2xs',
      highlighted
        ? 'border-accent bg-accent-dim text-content'
        : 'border-transparent text-content-muted'
    )}
  >
    <span className="w-12 shrink-0 select-none text-right text-content-subtle">{event.line_no}</span>
    <span className="w-14 shrink-0 uppercase text-content-subtle">{event.level}</span>
    <span className="min-w-0 flex-1 whitespace-pre-wrap break-words">{event.message}</span>
  </div>
);

export const EventDetailDrawer = ({
  event,
  onClose
}: {
  event: EventRecord | null;
  onClose: () => void;
}) => {
  const [tab, setTab] = useState<TabId>('context');

  const contextQuery = useQuery({
    queryKey: ['event-context', event?.id],
    queryFn: () => getEventContext(event!.id),
    enabled: Boolean(event)
  });

  const similarQuery = useQuery({
    queryKey: ['event-similar', event?.id],
    queryFn: () => getSimilarEvents(event!.id, 8),
    enabled: Boolean(event) && tab === 'similar'
  });

  if (!event) return null;

  return (
    <Drawer
      open={Boolean(event)}
      onClose={onClose}
      title={event.message || '(empty log line)'}
      subtitle={
        <span className="flex flex-wrap items-center gap-2">
          <LevelBadge level={event.level} />
          <ServiceBadge service={event.service} />
          <StatusCodeBadge code={event.status_code} />
          <CategoryBadge category={event.error_category} />
          <span title={formatDate(event.timestamp)}>{formatRelative(event.timestamp)}</span>
        </span>
      }
    >
      <div className="space-y-4 p-5">
        <section className="panel-raised p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-content-subtle">
            Event
          </h3>
          <dl>
            <Field label="Event ID" value={event.id} mono copyable={event.id} />
            <Field label="Timestamp" value={formatDate(event.timestamp)} mono />
            <Field label="Service" value={event.service} mono />
            <Field label="Level" value={event.level} mono />
            <Field label="Line" value={`#${event.line_no}`} mono />
            <Field label="File ID" value={event.file_id} mono copyable={event.file_id} />
            {event.trace_id && (
              <Field label="Trace ID" value={event.trace_id} mono copyable={event.trace_id} />
            )}
            {event.span_id && <Field label="Span ID" value={event.span_id} mono />}
            {event.correlation_id && <Field label="Correlation ID" value={event.correlation_id} mono />}
            {event.http_method && <Field label="Method" value={event.http_method} mono />}
            {event.path && <Field label="Endpoint" value={event.path} mono copyable={event.path} />}
            {event.status_code && <Field label="Status" value={event.status_code} mono />}
            {event.exception && <Field label="Exception" value={event.exception} mono />}
            {event.language && <Field label="Language" value={titleCase(event.language)} />}
            {event.framework && <Field label="Framework" value={titleCase(event.framework)} />}
            <Field label="Category" value={titleCase(event.error_category)} />
            <Field label="Embedding" value={titleCase(event.embedding_status)} />
          </dl>
        </section>

        {event.incident_id ? (
          <Link
            to={`/incidents/${event.incident_id}`}
            className="panel-raised flex items-center gap-3 p-4 transition-colors hover:border-line-strong"
          >
            <ShieldAlert size={16} className="shrink-0 text-severity-medium" aria-hidden />
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium text-content">Part of a grouped incident</div>
              <div className="mt-0.5 text-2xs text-content-subtle">
                Open the incident workspace to see the full picture
              </div>
            </div>
            <ExternalLink size={14} className="shrink-0 text-content-subtle" aria-hidden />
          </Link>
        ) : (
          <div className="panel-raised px-4 py-3 text-2xs text-content-subtle">
            Not yet linked to an incident. Clustering groups this event once enough similar failures
            have been embedded.
          </div>
        )}

        <div className="flex gap-1 border-b border-line" role="tablist">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              onClick={() => setTab(item.id)}
              className={clsx(
                '-mb-px border-b-2 px-3 py-2 text-xs font-medium transition-colors',
                tab === item.id
                  ? 'border-accent text-content'
                  : 'border-transparent text-content-muted hover:text-content'
              )}
            >
              {item.label}
            </button>
          ))}
        </div>

        {tab === 'context' && (
          <section>
            {contextQuery.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, index) => (
                  <Skeleton key={index} className="h-5 w-full" />
                ))}
              </div>
            ) : contextQuery.isError ? (
              <ErrorState
                message={errorMessage(contextQuery.error)}
                onRetry={() => contextQuery.refetch()}
              />
            ) : (
              <>
                <p className="mb-2 text-2xs text-content-subtle">
                  Resolved using{' '}
                  <span className="font-medium text-content-muted">
                    {titleCase(contextQuery.data?.strategy)}
                  </span>
                </p>
                <div className="overflow-hidden rounded-lg border border-line bg-canvas/60 py-1">
                  {contextQuery.data?.before.map((line) => (
                    <ContextLine key={line.id} event={line} />
                  ))}
                  <ContextLine event={event} highlighted />
                  {contextQuery.data?.after.map((line) => (
                    <ContextLine key={line.id} event={line} />
                  ))}
                </div>
              </>
            )}
          </section>
        )}

        {tab === 'similar' && (
          <section>
            {similarQuery.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-16 w-full" />
                ))}
              </div>
            ) : similarQuery.isError ? (
              <ErrorState
                message={errorMessage(similarQuery.error)}
                onRetry={() => similarQuery.refetch()}
              />
            ) : (similarQuery.data?.length ?? 0) === 0 ? (
              <EmptyState
                title="No similar events found"
                description="Similar events appear once embeddings have been generated for your logs."
              />
            ) : (
              <ul className="space-y-2">
                {similarQuery.data?.map((match) => (
                  <li key={match.event.id} className="panel-raised p-3">
                    <div className="flex items-center gap-2">
                      <LevelBadge level={match.event.level} />
                      <ServiceBadge service={match.event.service} />
                      <span className="ml-auto text-2xs font-medium text-accent-soft">
                        Similarity: {Math.round(match.score * 100)}%
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-2 font-mono text-2xs text-content-muted">
                      {match.event.message}
                    </p>
                    {match.matched_on.length > 0 && (
                      <p className="mt-1.5 text-2xs text-content-subtle">
                        Shared metadata: {match.matched_on.join(', ')}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {tab === 'notes' &&
          (event.incident_id ? (
            <NotesPanel incidentId={event.incident_id} eventId={event.id} />
          ) : (
            <EmptyState
              icon={<ShieldAlert size={18} />}
              title="Notes live on incidents"
              description="This event is not part of an incident yet. Once clustering groups it, you can record root-cause knowledge against the incident."
            />
          ))}

        {tab === 'raw' && (
          <section className="space-y-3">
            <Expandable title="Original log line" defaultOpen>
              <div className="flex items-start gap-2">
                <pre className="min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-words font-mono text-2xs text-content-muted">
                  {event.message}
                </pre>
                <CopyButton value={event.message} />
              </div>
            </Expandable>

            {event.stack_trace && (
              <Expandable title="Stack trace">
                <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-2xs text-content-muted">
                  {event.stack_trace}
                </pre>
              </Expandable>
            )}

            {contextQuery.data?.raw_chunk && (
              <Expandable title={`Raw chunk #${contextQuery.data.raw_chunk_sequence ?? 0}`}>
                <pre className="max-h-72 overflow-auto whitespace-pre font-mono text-2xs text-content-muted">
                  {contextQuery.data.raw_chunk}
                </pre>
              </Expandable>
            )}
          </section>
        )}
      </div>
    </Drawer>
  );
};

