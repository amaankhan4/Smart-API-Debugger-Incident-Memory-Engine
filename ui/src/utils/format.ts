import { format, formatDistanceToNow, isValid, parseISO } from 'date-fns';

const toDate = (value?: string | null): Date | null => {
  if (!value) return null;
  const parsed = typeof value === 'string' ? parseISO(value) : new Date(value);
  return isValid(parsed) ? parsed : null;
};

export const formatDate = (value?: string | null) => {
  const date = toDate(value);
  return date ? format(date, 'dd MMM yyyy, HH:mm:ss') : '—';
};

export const formatTimeOnly = (value?: string | null) => {
  const date = toDate(value);
  return date ? format(date, 'HH:mm:ss') : '—';
};

export const formatRelative = (value?: string | null) => {
  const date = toDate(value);
  return date ? formatDistanceToNow(date, { addSuffix: true }) : '—';
};

export const formatChartLabel = (value?: string | null) => {
  const date = toDate(value);
  return date ? format(date, 'dd MMM HH:mm') : '';
};

export const bytesToReadable = (bytes?: number | null) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
};

export const formatNumber = (value?: number | null) =>
  typeof value === 'number' ? new Intl.NumberFormat().format(value) : '0';

export const formatPercent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

export const formatDuration = (ms?: number | null) => {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
};

export const titleCase = (value?: string | null) =>
  (value ?? '').replace(/[_-]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());

export const debounce = <Args extends unknown[]>(fn: (...args: Args) => void, wait = 250) => {
  let timer: number | undefined;
  return (...args: Args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
};

export const copyToClipboard = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
};

