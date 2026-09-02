import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

type StatCardProps = {
  label: string;
  value: number | string;
  hint?: string;
  icon: LucideIcon;
  tone?: 'default' | 'critical' | 'warning' | 'success';
  to?: string;
};

const TONES = {
  default: 'text-content-muted',
  critical: 'text-severity-critical',
  warning: 'text-severity-medium',
  success: 'text-emerald-400'
} as const;

export const StatCard = ({ label, value, hint, icon: Icon, tone = 'default', to }: StatCardProps) => {
  const body = (
    <>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-content-muted">{label}</span>
        <Icon size={15} className={clsx('shrink-0', TONES[tone])} aria-hidden />
      </div>
      <div className="mt-3 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      {hint ? <div className="mt-1 text-xs text-content-subtle">{hint}</div> : null}
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        className="panel block p-5 transition-colors hover:border-line-strong hover:bg-surface-raised"
      >
        {body}
      </Link>
    );
  }
  return <div className="panel p-5">{body}</div>;
};

