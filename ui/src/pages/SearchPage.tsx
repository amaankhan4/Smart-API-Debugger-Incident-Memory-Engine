import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';
import { AlertTriangle, Search, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { errorMessage } from 'api/client';
import { searchEvents } from 'api/search';
import { EventCard } from 'components/EventCard';
import { EventDetailDrawer } from 'components/EventDetailDrawer';
import { PageHeader } from 'components/PageHeader';
import { EmptyState, ErrorState, Skeleton } from 'components/ui/States';
import type { EventRecord, SearchMode } from 'types/api';
import { formatDuration } from 'utils/format';

const MODES: { id: SearchMode; label: string; hint: string }[] = [
  { id: 'hybrid', label: 'Hybrid', hint: 'Combines meaning and exact wording' },
  { id: 'semantic', label: 'Semantic', hint: 'Finds events that mean the same thing' },
  { id: 'keyword', label: 'Keyword', hint: 'Matches the literal text' }
];

const EXAMPLES = [
  'database connection timeout after deployment',
  'payment gateway returned 502',
  'authentication token expired'
];

export const SearchPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [draft, setDraft] = useState(searchParams.get('q') ?? '');
  const [query, setQuery] = useState(searchParams.get('q') ?? '');
  const [mode, setMode] = useState<SearchMode>('hybrid');
  const [selected, setSelected] = useState<EventRecord | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(draft.trim()), 350);
    return () => window.clearTimeout(timer);
  }, [draft]);

  useEffect(() => {
    if (query) setSearchParams({ q: query }, { replace: true });
  }, [query, setSearchParams]);

  const searchQuery = useQuery({
    queryKey: ['search', query, mode],
    queryFn: () => searchEvents({ q: query, mode, limit: 40 }),
    enabled: query.length > 0
  });

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="Search"
        description="Ask in plain language. Semantic search finds events that mean the same thing, even when the wording differs."
      />

      <div className="panel p-4">
        <div className="flex items-center gap-3 rounded-lg border border-line bg-surface-raised px-3">
          <Search size={16} className="shrink-0 text-content-subtle" aria-hidden />
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="database connection timeout after deployment"
            aria-label="Search query"
            autoFocus
            className="w-full bg-transparent py-2.5 text-sm outline-none placeholder:text-content-subtle"
          />
          {searchQuery.isFetching && (
            <span className="shrink-0 text-2xs text-content-subtle">searching…</span>
          )}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setMode(item.id)}
              title={item.hint}
              aria-pressed={mode === item.id}
              className={clsx(
                'chip transition-colors',
                mode === item.id
                  ? 'border-accent/40 bg-accent-dim text-accent-soft'
                  : 'border-line bg-surface-raised text-content-subtle hover:text-content-muted'
              )}
            >
              {item.label}
            </button>
          ))}
          {searchQuery.data && (
            <span className="ml-auto text-2xs text-content-subtle">
              {searchQuery.data.total} results in {formatDuration(searchQuery.data.took_ms)}
            </span>
          )}
        </div>
      </div>

      <div className="mt-4">
        {searchQuery.data?.degraded_reason && (
          <div
            role="status"
            className="mb-3 flex items-start gap-2 rounded-lg border border-severity-high/40 bg-severity-high/10 px-3 py-2 text-xs text-severity-high"
          >
            <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden />
            <span>
              <span className="font-medium">Keyword results only. </span>
              <span className="text-content-muted">
                {searchQuery.data.degraded_reason === 'vector_quota_exceeded'
                  ? 'The daily vector quota is spent, so semantic ranking is paused until it resets at midnight UTC.'
                  : 'The vector store is unreachable, so semantic ranking is unavailable right now.'}
              </span>
            </span>
          </div>
        )}
        {!query ? (
          <div className="panel">
            <EmptyState
              icon={<Sparkles size={18} />}
              title="Search your incident memory"
              description="Describe the failure the way you would to a colleague. Try one of these:"
              action={
                <div className="flex flex-col gap-2">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setDraft(example)}
                      className="btn-secondary text-xs"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              }
            />
          </div>
        ) : searchQuery.isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-24 w-full" />
            ))}
          </div>
        ) : searchQuery.isError ? (
          <div className="panel">
            <ErrorState
              message={errorMessage(searchQuery.error)}
              onRetry={() => searchQuery.refetch()}
            />
          </div>
        ) : searchQuery.data?.results.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={<Search size={18} />}
              title="No matching events"
              description="Nothing in your ingested logs resembles this query. Try different wording, or switch to keyword mode for an exact match."
            />
          </div>
        ) : (
          <ul className="space-y-2">
            {searchQuery.data?.results.map((result) => (
              <li key={result.event.id}>
                <EventCard
                  event={result.event}
                  score={result.score}
                  matchedOn={result.matched_on}
                  onClick={() => setSelected(result.event)}
                  selected={selected?.id === result.event.id}
                />
              </li>
            ))}
          </ul>
        )}
      </div>

      <EventDetailDrawer event={selected} onClose={() => setSelected(null)} />
    </div>
  );
};
