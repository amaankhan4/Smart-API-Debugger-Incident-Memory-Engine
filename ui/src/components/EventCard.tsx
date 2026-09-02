import clsx from 'clsx';

import { CategoryBadge, LevelBadge, ServiceBadge, StatusCodeBadge } from 'components/ui/Badges';
import type { EventRecord } from 'types/api';
import { formatDate, formatRelative } from 'utils/format';

type EventCardProps = {
  event: EventRecord;
  onClick?: () => void;
  score?: number;
  matchedOn?: string[];
  selected?: boolean;
};

export const EventCard = ({ event, onClick, score, matchedOn, selected }: EventCardProps) => (
  <button
    type="button"
    onClick={onClick}
    className={clsx(
      'panel w-full p-4 text-left transition-colors hover:border-line-strong hover:bg-surface-raised',
      selected && 'border-accent/50 bg-accent-dim'
    )}
  >
    <div className="flex flex-wrap items-center gap-2">
      <LevelBadge level={event.level} />
      <ServiceBadge service={event.service} />
      <StatusCodeBadge code={event.status_code} />
      <CategoryBadge category={event.error_category} />
      {typeof score === 'number' && (
        <span className="chip border-accent/30 bg-accent-dim text-accent-soft">
          {Math.round(score * 100)}% match
        </span>
      )}
      <span
        className="ml-auto shrink-0 text-2xs text-content-subtle"
        title={formatDate(event.timestamp)}
      >
        {formatRelative(event.timestamp)}
      </span>
    </div>

    <p className="mt-2.5 line-clamp-2 font-mono text-xs leading-relaxed text-content">
      {event.message || <span className="text-content-subtle">(empty log line)</span>}
    </p>

    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-content-subtle">
      <span>line {event.line_no}</span>
      {event.exception && <span className="font-mono">{event.exception}</span>}
      {event.path && <span className="font-mono">{event.http_method} {event.path}</span>}
      {matchedOn && matchedOn.length > 0 && (
        <span className="text-accent-soft">matched on {matchedOn.join(', ')}</span>
      )}
    </div>
  </button>
);

