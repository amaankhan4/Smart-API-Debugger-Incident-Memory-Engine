import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Clock } from 'lucide-react';

import { getVectorQuota } from 'api/system';
import { useAuthStore } from 'store/useAuthStore';

const WARN_AT = 0.8;

const formatReset = (iso: string) => {
  const resets = new Date(iso).getTime() - Date.now();
  if (!Number.isFinite(resets) || resets <= 0) return 'shortly';
  const hours = Math.floor(resets / 3_600_000);
  const minutes = Math.round((resets % 3_600_000) / 60_000);
  return hours > 0 ? `in ${hours}h ${minutes}m` : `in ${minutes}m`;
};

/** Warns before the daily Upstash Vector allowance runs out, and explains it once it has. */
export const QuotaBanner = () => {
  const authenticated = useAuthStore((state) => state.status === 'authenticated');

  const { data } = useQuery({
    queryKey: ['vector-quota'],
    queryFn: getVectorQuota,
    enabled: authenticated,
    refetchInterval: 60_000,
    staleTime: 45_000
  });

  if (!data) return null;

  const updateRatio = data.updates_limit ? data.updates_used / data.updates_limit : 0;
  const queryRatio = data.queries_limit ? data.queries_used / data.queries_limit : 0;
  const worst = Math.max(updateRatio, queryRatio);

  if (!data.exhausted && worst < WARN_AT) return null;

  const resetsIn = formatReset(data.resets_at);

  return (
    <div
      role="status"
      className={
        data.exhausted
          ? 'flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-severity-critical/40 bg-severity-critical/10 px-4 py-2 text-xs text-severity-critical'
          : 'flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-severity-high/40 bg-severity-high/10 px-4 py-2 text-xs text-severity-high'
      }
    >
      <AlertTriangle size={14} className="shrink-0" aria-hidden />
      <span className="font-medium">
        {data.exhausted
          ? 'Daily vector quota reached.'
          : `Daily vector quota ${Math.round(worst * 100)}% used.`}
      </span>
      <span className="text-content-muted">
        {data.exhausted
          ? 'New logs stay queued and search falls back to keyword matching.'
          : 'Semantic indexing pauses when it runs out.'}
      </span>
      <span className="ml-auto inline-flex items-center gap-1 text-content-subtle">
        <Clock size={12} aria-hidden />
        Resets {resetsIn}
        <span className="hidden sm:inline">
          · {data.updates_used.toLocaleString()}/{data.updates_limit.toLocaleString()} writes ·{' '}
          {data.queries_used.toLocaleString()}/{data.queries_limit.toLocaleString()} reads
        </span>
      </span>
    </div>
  );
};
