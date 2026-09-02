import { useInfiniteQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import clsx from 'clsx';
import { Filter, Loader2, RotateCcw, Terminal, Upload } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { errorMessage } from 'api/client';
import { getEvent, getEvents } from 'api/events';
import { getFiles } from 'api/files';
import { EventDetailDrawer } from 'components/EventDetailDrawer';
import { PageHeader } from 'components/PageHeader';
import { CategoryBadge, LevelBadge, StatusCodeBadge } from 'components/ui/Badges';
import { EmptyState, ErrorState, TableSkeleton } from 'components/ui/States';
import { useUiStore } from 'store/useUiStore';
import type { ErrorCategory, EventRecord, LogLevel } from 'types/api';
import { formatNumber, formatTimeOnly } from 'utils/format';
import { useQuery } from '@tanstack/react-query';

const PAGE_SIZE = 100;
const ROW_HEIGHT = 40;

const LEVELS: LogLevel[] = ['CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE'];
const CATEGORIES: ErrorCategory[] = [
  'database',
  'network',
  'authentication',
  'authorization',
  'validation',
  'timeout',
  'rate_limit',
  'dependency',
  'configuration',
  'unknown'
];

export const LogExplorerPage = () => {
  const filters = useUiStore((state) => state.logFilters);
  const setFilters = useUiStore((state) => state.setLogFilters);
  const resetFilters = useUiStore((state) => state.resetLogFilters);

  const [searchParams, setSearchParams] = useSearchParams();
  const [searchDraft, setSearchDraft] = useState(filters.search);
  const [selected, setSelected] = useState<EventRecord | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Deep links from the palette/overview open a specific event directly.
  const deepLinkId = searchParams.get('event');
  const deepLinkQuery = useQuery({
    queryKey: ['event', deepLinkId],
    queryFn: () => getEvent(deepLinkId!),
    enabled: Boolean(deepLinkId)
  });

  useEffect(() => {
    if (deepLinkQuery.data) setSelected(deepLinkQuery.data);
  }, [deepLinkQuery.data]);

  useEffect(() => {
    if (searchParams.get('only_errors') === '1' && !filters.onlyErrors) {
      setFilters({ onlyErrors: true });
      searchParams.delete('only_errors');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams, filters.onlyErrors, setFilters]);

  useEffect(() => {
    const timer = window.setTimeout(() => setFilters({ search: searchDraft }), 300);
    return () => window.clearTimeout(timer);
  }, [searchDraft, setFilters]);

  const filesQuery = useQuery({ queryKey: ['files', 'select'], queryFn: () => getFiles({ limit: 100 }) });

  const eventsQuery = useInfiniteQuery({
    queryKey: ['events', 'explorer', filters],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      getEvents({
        search: filters.search || undefined,
        level: filters.level,
        service: filters.service || undefined,
        file_id: filters.fileId || undefined,
        error_category: filters.errorCategory,
        only_errors: filters.onlyErrors || undefined,
        limit: PAGE_SIZE,
        offset: pageParam as number
      }),
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.offset + lastPage.items.length;
      return loaded < lastPage.total ? loaded : undefined;
    }
  });

  const events = useMemo(
    () => eventsQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [eventsQuery.data]
  );
  const total = eventsQuery.data?.pages[0]?.total ?? 0;

  const virtualizer = useVirtualizer({
    count: events.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12
  });

  // Fetch the next page as the user approaches the end of the loaded rows.
  const virtualItems = virtualizer.getVirtualItems();
  useEffect(() => {
    const last = virtualItems[virtualItems.length - 1];
    if (!last) return;
    if (last.index >= events.length - 20 && eventsQuery.hasNextPage && !eventsQuery.isFetchingNextPage) {
      void eventsQuery.fetchNextPage();
    }
  }, [virtualItems, events.length, eventsQuery]);

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (events.length === 0) return;
      if (event.key === 'ArrowDown' || event.key === 'j') {
        event.preventDefault();
        setActiveIndex((index) => {
          const next = Math.min(index + 1, events.length - 1);
          virtualizer.scrollToIndex(next);
          return next;
        });
      }
      if (event.key === 'ArrowUp' || event.key === 'k') {
        event.preventDefault();
        setActiveIndex((index) => {
          const next = Math.max(index - 1, 0);
          virtualizer.scrollToIndex(next);
          return next;
        });
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        setSelected(events[activeIndex] ?? null);
      }
    },
    [events, activeIndex, virtualizer]
  );

  const hasActiveFilters =
    Boolean(filters.search) ||
    Boolean(filters.level) ||
    Boolean(filters.service) ||
    Boolean(filters.fileId) ||
    Boolean(filters.errorCategory) ||
    filters.onlyErrors;

  return (
    <div className="mx-auto flex h-full max-w-[1600px] flex-col">
      <PageHeader
        title="Log Explorer"
        description="Filter, scan and open any structured event extracted from your logs."
        actions={
          <span className="text-xs text-content-subtle">
            {formatNumber(total)} matching events
          </span>
        }
      />

      <div className="panel mb-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <label htmlFor="log-search" className="mb-1.5 block text-xs font-medium text-content-muted">
              Message contains
            </label>
            <input
              id="log-search"
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="connection timeout"
              className="input"
            />
          </div>

          <div>
            <label htmlFor="log-level" className="mb-1.5 block text-xs font-medium text-content-muted">
              Level
            </label>
            <select
              id="log-level"
              value={filters.level ?? ''}
              onChange={(event) =>
                setFilters({ level: (event.target.value || undefined) as LogLevel | undefined })
              }
              className="input w-36"
            >
              <option value="">All levels</option>
              {LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="log-service" className="mb-1.5 block text-xs font-medium text-content-muted">
              Service
            </label>
            <input
              id="log-service"
              value={filters.service ?? ''}
              onChange={(event) => setFilters({ service: event.target.value || undefined })}
              placeholder="auth-service"
              className="input w-40"
            />
          </div>

          <div>
            <label htmlFor="log-category" className="mb-1.5 block text-xs font-medium text-content-muted">
              Category
            </label>
            <select
              id="log-category"
              value={filters.errorCategory ?? ''}
              onChange={(event) =>
                setFilters({
                  errorCategory: (event.target.value || undefined) as ErrorCategory | undefined
                })
              }
              className="input w-40"
            >
              <option value="">All categories</option>
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="log-file" className="mb-1.5 block text-xs font-medium text-content-muted">
              File
            </label>
            <select
              id="log-file"
              value={filters.fileId ?? ''}
              onChange={(event) => setFilters({ fileId: event.target.value || undefined })}
              className="input w-44"
            >
              <option value="">All files</option>
              {filesQuery.data?.items.map((file) => (
                <option key={file.file_id} value={file.file_id}>
                  {file.filename}
                </option>
              ))}
            </select>
          </div>

          <label className="flex cursor-pointer items-center gap-2 pb-2 text-xs text-content-muted">
            <input
              type="checkbox"
              checked={filters.onlyErrors}
              onChange={(event) => setFilters({ onlyErrors: event.target.checked })}
              className="h-3.5 w-3.5 rounded border-line bg-surface-raised accent-[#6E7BFF]"
            />
            Errors only
          </label>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                resetFilters();
                setSearchDraft('');
              }}
              className="btn-ghost mb-1 px-2 py-1 text-xs"
            >
              <RotateCcw size={12} />
              Clear
            </button>
          )}
        </div>
      </div>

      <section className="panel flex min-h-0 flex-1 flex-col">
        <div className="flex shrink-0 items-center gap-3 border-b border-line px-4 py-2 text-2xs uppercase tracking-wide text-content-subtle">
          <span className="w-16 shrink-0">Time</span>
          <span className="w-20 shrink-0">Level</span>
          <span className="w-32 shrink-0">Service</span>
          <span className="min-w-0 flex-1">Message</span>
          <span className="hidden w-28 shrink-0 text-right lg:block">Endpoint</span>
        </div>

        {eventsQuery.isLoading ? (
          <TableSkeleton rows={12} columns={5} />
        ) : eventsQuery.isError ? (
          <ErrorState message={errorMessage(eventsQuery.error)} onRetry={() => eventsQuery.refetch()} />
        ) : events.length === 0 ? (
          <EmptyState
            icon={hasActiveFilters ? <Filter size={18} /> : <Terminal size={18} />}
            title={hasActiveFilters ? 'No events match these filters' : 'No events yet'}
            description={
              hasActiveFilters
                ? 'Try widening the level, service or time filters.'
                : 'Upload and ingest a log file to turn raw lines into structured, searchable events.'
            }
            action={
              hasActiveFilters ? (
                <button
                  type="button"
                  onClick={() => {
                    resetFilters();
                    setSearchDraft('');
                  }}
                  className="btn-secondary"
                >
                  Clear filters
                </button>
              ) : (
                <Link to="/files?upload=1" className="btn-primary">
                  <Upload size={14} />
                  Upload a log file
                </Link>
              )
            }
          />
        ) : (
          <div
            ref={scrollRef}
            tabIndex={0}
            onKeyDown={onKeyDown}
            role="listbox"
            aria-label="Log events"
            className="min-h-0 flex-1 overflow-auto outline-none"
          >
            <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
              {virtualItems.map((virtualRow) => {
                const event = events[virtualRow.index];
                if (!event) return null;
                const isActive = virtualRow.index === activeIndex;
                return (
                  <div
                    key={event.id}
                    role="option"
                    aria-selected={isActive}
                    onClick={() => {
                      setActiveIndex(virtualRow.index);
                      setSelected(event);
                    }}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: virtualRow.size,
                      transform: `translateY(${virtualRow.start}px)`
                    }}
                    className={clsx(
                      'flex cursor-pointer items-center gap-3 border-b border-line/50 px-4 text-xs transition-colors',
                      isActive ? 'bg-accent-dim' : 'hover:bg-surface-hover'
                    )}
                  >
                    <span className="w-16 shrink-0 font-mono text-content-subtle">
                      {formatTimeOnly(event.timestamp)}
                    </span>
                    <span className="w-20 shrink-0">
                      <LevelBadge level={event.level} />
                    </span>
                    <span className="w-32 shrink-0 truncate font-mono text-content-muted">
                      {event.service}
                    </span>
                    <span className="min-w-0 flex-1 truncate font-mono text-content">
                      {event.message}
                    </span>
                    <span className="hidden w-28 shrink-0 items-center justify-end gap-1 lg:flex">
                      <StatusCodeBadge code={event.status_code} />
                      <CategoryBadge category={event.error_category} />
                    </span>
                  </div>
                );
              })}
            </div>

            {eventsQuery.isFetchingNextPage && (
              <div className="flex items-center justify-center gap-2 py-3 text-xs text-content-subtle">
                <Loader2 size={13} className="animate-spin" aria-hidden />
                Loading more events…
              </div>
            )}
          </div>
        )}

        <footer className="shrink-0 border-t border-line px-4 py-2 text-2xs text-content-subtle">
          <span className="kbd">↑</span> <span className="kbd">↓</span> navigate ·{' '}
          <span className="kbd">↵</span> open · showing {formatNumber(events.length)} of{' '}
          {formatNumber(total)}
        </footer>
      </section>

      <EventDetailDrawer
        event={selected}
        onClose={() => {
          setSelected(null);
          if (deepLinkId) {
            searchParams.delete('event');
            setSearchParams(searchParams, { replace: true });
          }
        }}
      />
    </div>
  );
};

