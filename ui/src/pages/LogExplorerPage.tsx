import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEvents, getSimilarEvents } from 'api/events';
import { EventCard } from 'components/EventCard';
import { EventDetailDrawer } from 'components/EventDetailDrawer';
import type { EventRecord } from 'types/api';
import { debounce } from 'utils/format';
import { useUiStore } from 'store/useUiStore';

export const LogExplorerPage = () => {
  const smartSearch = useUiStore((state) => state.smartSearch);
  const [selectedEvent, setSelectedEvent] = useState<EventRecord | null>(null);
  const [filters, setFilters] = useState({ level: '', service: '', file_id: '' });
  const [semanticQuery, setSemanticQuery] = useState(smartSearch);
  const [debouncedQuery, setDebouncedQuery] = useState(smartSearch);

  const setDebounced = useMemo(() => debounce((val: string) => setDebouncedQuery(val), 300), []);

  const eventsQuery = useQuery({
    queryKey: ['events', filters],
    queryFn: () => getEvents({ ...filters, limit: 200 })
  });

  const smartQuery = useQuery({
    queryKey: ['smart-search', debouncedQuery],
    queryFn: () => getSimilarEvents(debouncedQuery, 20),
    enabled: debouncedQuery.trim().length > 2
  });

  const events = debouncedQuery.trim().length > 2
    ? (smartQuery.data?.matches.map((match) => match.event) ?? [])
    : (eventsQuery.data?.items ?? []);

  return (
    <section className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside className="card h-fit p-4">
        <h2 className="text-sm font-semibold">Filters</h2>
        <div className="mt-3 space-y-3">
          <div>
            <label className="mb-1 block text-xs text-slate-400">Level</label>
            <select className="input" value={filters.level} onChange={(e) => setFilters((prev) => ({ ...prev, level: e.target.value }))}>
              <option value="">All</option>
              <option value="ERROR">ERROR</option>
              <option value="WARN">WARN</option>
              <option value="INFO">INFO</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Service</label>
            <input className="input" placeholder="auth-service" value={filters.service} onChange={(e) => setFilters((prev) => ({ ...prev, service: e.target.value }))} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">File ID</label>
            <input className="input" placeholder="uuid" value={filters.file_id} onChange={(e) => setFilters((prev) => ({ ...prev, file_id: e.target.value }))} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Smart Search</label>
            <input
              className="input"
              placeholder='"SOAP rate limit error"'
              value={semanticQuery}
              onChange={(e) => {
                const val = e.target.value;
                setSemanticQuery(val);
                setDebounced(val);
              }}
            />
          </div>
        </div>
      </aside>

      <section className="space-y-3">
        {events.map((event) => (
          <EventCard key={event.id} event={event} onClick={() => setSelectedEvent(event)} />
        ))}
        {events.length === 0 && <div className="card p-5 text-sm text-slate-400">No events found.</div>}
      </section>

      <EventDetailDrawer event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </section>
  );
};
