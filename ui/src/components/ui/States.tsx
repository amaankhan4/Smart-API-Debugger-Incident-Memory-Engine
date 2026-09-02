import clsx from 'clsx';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { ReactNode } from 'react';

export const Skeleton = ({ className }: { className?: string }) => (
  <div className={clsx('skeleton', className)} aria-hidden />
);

export const TableSkeleton = ({ rows = 8, columns = 5 }: { rows?: number; columns?: number }) => (
  <div className="divide-y divide-line" role="status" aria-label="Loading results">
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={rowIndex} className="flex items-center gap-4 px-4 py-3">
        {Array.from({ length: columns }).map((__, columnIndex) => (
          <Skeleton
            key={columnIndex}
            className={clsx('h-4', columnIndex === columns - 1 ? 'flex-1' : 'w-24')}
          />
        ))}
      </div>
    ))}
  </div>
);

export const CardSkeleton = ({ count = 4 }: { count?: number }) => (
  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" role="status" aria-label="Loading">
    {Array.from({ length: count }).map((_, index) => (
      <div key={index} className="panel p-5">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="mt-4 h-8 w-28" />
        <Skeleton className="mt-3 h-3 w-32" />
      </div>
    ))}
  </div>
);

export const ChartSkeleton = ({ className }: { className?: string }) => (
  <Skeleton className={clsx('h-64 w-full', className)} />
);

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
};

export const EmptyState = ({ icon, title, description, action, className }: EmptyStateProps) => (
  <div
    className={clsx('flex flex-col items-center justify-center px-6 py-16 text-center', className)}
  >
    {icon && (
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-surface-raised text-content-muted">
        {icon}
      </div>
    )}
    <h3 className="text-sm font-semibold text-content">{title}</h3>
    <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-content-muted">{description}</p>
    {action && <div className="mt-5">{action}</div>}
  </div>
);

type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
};

export const ErrorState = ({
  title = 'Something went wrong',
  message,
  onRetry,
  className
}: ErrorStateProps) => (
  <div
    role="alert"
    className={clsx('flex flex-col items-center justify-center px-6 py-16 text-center', className)}
  >
    <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-severity-critical/40 bg-severity-critical/10 text-severity-critical">
      <AlertTriangle size={18} />
    </div>
    <h3 className="text-sm font-semibold text-content">{title}</h3>
    <p className="mt-1.5 max-w-md break-words text-sm leading-relaxed text-content-muted">{message}</p>
    {onRetry && (
      <button type="button" onClick={onRetry} className="btn-secondary mt-5">
        <RefreshCw size={14} />
        Try again
      </button>
    )}
  </div>
);

/** Renders loading, error, empty and ready states so no screen can hang on a spinner. */
export function AsyncBoundary({
  isLoading,
  isError,
  error,
  onRetry,
  isEmpty,
  loadingFallback,
  emptyFallback,
  children
}: {
  isLoading: boolean;
  isError: boolean;
  error?: string;
  onRetry?: () => void;
  isEmpty?: boolean;
  loadingFallback: ReactNode;
  emptyFallback?: ReactNode;
  children: ReactNode;
}) {
  if (isLoading) return <>{loadingFallback}</>;
  if (isError) return <ErrorState message={error ?? 'Unexpected error'} onRetry={onRetry} />;
  if (isEmpty && emptyFallback) return <>{emptyFallback}</>;
  return <>{children}</>;
}
