import type { EventRecord } from 'types/api';
import { formatDate } from 'utils/format';

type EventCardProps = {
  event: EventRecord;
  onClick?: () => void;
};

const levelStyle: Record<string, string> = {
  ERROR: 'bg-rose-500/20 text-rose-200 border-rose-500/30',
  WARN: 'bg-amber-500/20 text-amber-200 border-amber-500/30',
  INFO: 'bg-sky-500/20 text-sky-200 border-sky-500/30'
};

export const EventCard = ({ event, onClick }: EventCardProps) => (
  <button onClick={onClick} className="card w-full p-4 text-left transition hover:border-indigo-400/50">
    <div className="mb-2 flex items-center gap-2">
      <span className={`rounded border px-2 py-0.5 text-xs ${levelStyle[event.level] ?? levelStyle.INFO}`}>
        {event.level}
      </span>
      <span className="text-xs text-slate-400">{event.service ?? 'unknown-service'}</span>
      <span className="ml-auto text-xs text-slate-500">{formatDate(event.timestamp)}</span>
    </div>
    <p className="line-clamp-2 text-sm text-slate-200">{event.message}</p>
    <p className="mt-2 text-xs text-slate-500">file_id: {event.file_id}</p>
  </button>
);
