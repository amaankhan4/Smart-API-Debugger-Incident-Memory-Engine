import type { ReactNode } from 'react';

export const PageHeader = ({
  title,
  description,
  actions,
  breadcrumbs
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  breadcrumbs?: ReactNode;
}) => (
  <header className="mb-6">
    {breadcrumbs && <div className="mb-2 text-xs text-content-subtle">{breadcrumbs}</div>}
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-content-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  </header>
);
