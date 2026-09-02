import clsx from 'clsx';
import { Check, ChevronRight, Copy } from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { copyToClipboard } from 'utils/format';

export const CopyButton = ({
  value,
  label = 'Copy',
  className
}: {
  value: string;
  label?: string;
  className?: string;
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (await copyToClipboard(value)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? 'Copied' : label}
      aria-label={copied ? 'Copied to clipboard' : label}
      className={clsx('btn-ghost px-1.5 py-1', className)}
    >
      {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
    </button>
  );
};

export const Field = ({
  label,
  value,
  mono,
  copyable
}: {
  label: string;
  value?: ReactNode;
  mono?: boolean;
  copyable?: string;
}) => (
  <div className="flex items-start justify-between gap-3 border-b border-line/60 py-2 last:border-0">
    <dt className="shrink-0 text-xs text-content-subtle">{label}</dt>
    <dd
      className={clsx(
        'flex min-w-0 items-center gap-1 text-right text-xs text-content',
        mono && 'font-mono'
      )}
    >
      <span className="truncate">{value ?? <span className="text-content-subtle">—</span>}</span>
      {copyable && <CopyButton value={copyable} />}
    </dd>
  </div>
);

/** Collapsible raw payload viewer for stack traces and unstructured metadata. */
export const Expandable = ({
  title,
  children,
  defaultOpen = false
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 bg-surface-raised px-3 py-2 text-left text-xs font-medium text-content-muted hover:text-content"
      >
        <ChevronRight
          size={13}
          className={clsx('transition-transform', open && 'rotate-90')}
          aria-hidden
        />
        {title}
      </button>
      {open && <div className="border-t border-line bg-canvas/50 p-3">{children}</div>}
    </div>
  );
};
