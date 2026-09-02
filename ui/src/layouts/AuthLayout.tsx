import { Activity } from 'lucide-react';
import type { ReactNode } from 'react';

export const AuthLayout = ({
  title,
  subtitle,
  children,
  footer
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) => (
  <div className="flex min-h-full items-center justify-center bg-canvas px-4 py-12">
    <div className="w-full max-w-sm animate-slide-up">
      <div className="mb-8 flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-accent/30 bg-accent-dim text-accent-soft">
          <Activity size={17} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">Incident Memory Engine</div>
          <div className="text-2xs text-content-subtle">Semantic observability for engineers</div>
        </div>
      </div>

      <div className="panel p-6">
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-content-muted">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>

      <p className="mt-6 text-center text-sm text-content-muted">{footer}</p>
    </div>
  </div>
);
