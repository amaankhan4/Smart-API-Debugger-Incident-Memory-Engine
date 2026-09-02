import clsx from 'clsx';

import type { FileStatus, IncidentSeverity, IncidentStatus, LogLevel } from 'types/api';
import { titleCase } from 'utils/format';

const LEVEL_STYLES: Record<LogLevel, string> = {
  CRITICAL: 'border-severity-critical/40 bg-severity-critical/10 text-severity-critical',
  ERROR: 'border-severity-critical/30 bg-severity-critical/10 text-severity-critical',
  WARN: 'border-severity-medium/30 bg-severity-medium/10 text-severity-medium',
  INFO: 'border-line-strong bg-surface-hover text-content-muted',
  DEBUG: 'border-line bg-surface-hover text-content-subtle',
  TRACE: 'border-line bg-surface-hover text-content-subtle'
};

const SEVERITY_STYLES: Record<IncidentSeverity, string> = {
  critical: 'border-severity-critical/40 bg-severity-critical/10 text-severity-critical',
  high: 'border-severity-high/40 bg-severity-high/10 text-severity-high',
  medium: 'border-severity-medium/40 bg-severity-medium/10 text-severity-medium',
  low: 'border-severity-low/40 bg-severity-low/10 text-severity-low'
};

const INCIDENT_STATUS_STYLES: Record<IncidentStatus, string> = {
  open: 'border-severity-critical/40 bg-severity-critical/10 text-severity-critical',
  investigating: 'border-severity-medium/40 bg-severity-medium/10 text-severity-medium',
  resolved: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  ignored: 'border-line-strong bg-surface-hover text-content-subtle'
};

const FILE_STATUS_STYLES: Record<FileStatus, string> = {
  uploaded: 'border-line-strong bg-surface-hover text-content-muted',
  processing: 'border-accent/40 bg-accent-dim text-accent-soft',
  embedding: 'border-accent/40 bg-accent-dim text-accent-soft',
  analyzing: 'border-accent/40 bg-accent-dim text-accent-soft',
  completed: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  failed: 'border-severity-critical/40 bg-severity-critical/10 text-severity-critical'
};

export const LevelBadge = ({ level }: { level: LogLevel }) => (
  <span className={clsx('chip font-mono uppercase', LEVEL_STYLES[level] ?? LEVEL_STYLES.INFO)}>
    {level}
  </span>
);

export const SeverityBadge = ({ severity }: { severity: IncidentSeverity }) => (
  <span className={clsx('chip', SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.low)}>
    <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
    {titleCase(severity)}
  </span>
);

export const IncidentStatusBadge = ({ status }: { status: IncidentStatus }) => (
  <span className={clsx('chip', INCIDENT_STATUS_STYLES[status] ?? INCIDENT_STATUS_STYLES.open)}>
    {titleCase(status)}
  </span>
);

export const FileStatusBadge = ({ status }: { status: FileStatus }) => {
  const inFlight = status === 'processing' || status === 'embedding' || status === 'analyzing';
  return (
    <span className={clsx('chip', FILE_STATUS_STYLES[status] ?? FILE_STATUS_STYLES.uploaded)}>
      {inFlight && (
        <span
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-current"
          aria-hidden
        />
      )}
      {titleCase(status)}
    </span>
  );
};

export const ServiceBadge = ({ service }: { service?: string | null }) => (
  <span className="chip border-line-strong bg-surface-hover font-mono text-content-muted">
    {service || 'unknown'}
  </span>
);

export const CategoryBadge = ({ category }: { category?: string | null }) => {
  if (!category || category === 'unknown') return null;
  return (
    <span className="chip border-accent/30 bg-accent-dim text-accent-soft">{titleCase(category)}</span>
  );
};

export const StatusCodeBadge = ({ code }: { code?: number | null }) => {
  if (!code) return null;
  const tone =
    code >= 500
      ? 'border-severity-critical/40 bg-severity-critical/10 text-severity-critical'
      : code >= 400
        ? 'border-severity-medium/40 bg-severity-medium/10 text-severity-medium'
        : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400';
  return <span className={clsx('chip font-mono', tone)}>{code}</span>;
};
