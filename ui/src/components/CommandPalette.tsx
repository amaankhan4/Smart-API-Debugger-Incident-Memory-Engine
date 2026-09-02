import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';
import { AnimatePresence, motion } from 'framer-motion';
import {
  BarChart3,
  CornerDownLeft,
  FileText,
  LayoutDashboard,
  Search,
  ShieldAlert,
  Terminal,
  Upload
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';

import { searchEvents } from 'api/search';
import { useUiStore } from 'store/useUiStore';
import { formatRelative } from 'utils/format';

type Command = {
  id: string;
  label: string;
  hint?: string;
  icon: ReactNode;
  run: () => void;
};

export const CommandPalette = () => {
  const navigate = useNavigate();
  const open = useUiStore((state) => state.commandPaletteOpen);
  const setOpen = useUiStore((state) => state.setCommandPaletteOpen);
  const toggle = useUiStore((state) => state.toggleCommandPalette);

  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        toggle();
      }
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [toggle, setOpen]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      window.setTimeout(() => inputRef.current?.focus(), 20);
    }
  }, [open]);

  const go = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  const navigationCommands = useMemo<Command[]>(
    () => [
      { id: 'overview', label: 'Go to Overview', icon: <LayoutDashboard size={15} />, run: () => go('/overview') },
      { id: 'files', label: 'Go to Files', icon: <FileText size={15} />, run: () => go('/files') },
      { id: 'upload', label: 'Upload a log file', icon: <Upload size={15} />, run: () => go('/files?upload=1') },
      { id: 'logs', label: 'Open Log Explorer', icon: <Terminal size={15} />, run: () => go('/logs') },
      { id: 'incidents', label: 'Open Incidents', icon: <ShieldAlert size={15} />, run: () => go('/incidents') },
      { id: 'analytics', label: 'Go to Analytics', icon: <BarChart3 size={15} />, run: () => go('/analytics') }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const trimmed = query.trim();
  const { data: searchData, isFetching } = useQuery({
    queryKey: ['palette-search', trimmed],
    queryFn: () => searchEvents({ q: trimmed, limit: 6 }),
    enabled: open && trimmed.length >= 3,
    staleTime: 15_000
  });

  const filteredNavigation = navigationCommands.filter((command) =>
    command.label.toLowerCase().includes(trimmed.toLowerCase())
  );

  const searchCommands: Command[] = (searchData?.results ?? []).map((result) => ({
    id: result.event.id,
    label: result.event.message.slice(0, 90) || '(empty log line)',
    hint: `${result.event.service} · ${formatRelative(result.event.timestamp)}`,
    icon: <Search size={15} />,
    run: () => go(`/logs?event=${result.event.id}`)
  }));

  const allCommands = [...filteredNavigation, ...searchCommands];
  const runFullSearch: Command | null = trimmed
    ? {
        id: 'full-search',
        label: `Search all logs for "${trimmed}"`,
        icon: <Search size={15} />,
        run: () => go(`/search?q=${encodeURIComponent(trimmed)}`)
      }
    : null;

  const commands = runFullSearch ? [runFullSearch, ...allCommands] : allCommands;

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % Math.max(commands.length, 1));
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + commands.length) % Math.max(commands.length, 1));
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      commands[activeIndex]?.run();
    }
  };

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={{ opacity: 0, scale: 0.98, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: -8 }}
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-full max-w-xl overflow-hidden rounded-xl border border-line bg-surface shadow-overlay"
          >
            <div className="flex items-center gap-3 border-b border-line px-4">
              <Search size={16} className="shrink-0 text-content-subtle" aria-hidden />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActiveIndex(0);
                }}
                onKeyDown={onKeyDown}
                placeholder="Search logs or jump to a page…"
                aria-label="Command palette input"
                className="w-full bg-transparent py-3.5 text-sm text-content outline-none placeholder:text-content-subtle"
              />
              {isFetching && <span className="text-2xs text-content-subtle">searching…</span>}
            </div>

            <ul className="max-h-80 overflow-y-auto py-2" role="listbox">
              {commands.length === 0 && (
                <li className="px-4 py-8 text-center text-sm text-content-muted">
                  No matching commands or logs.
                </li>
              )}
              {commands.map((command, index) => (
                <li key={command.id} role="option" aria-selected={index === activeIndex}>
                  <button
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={command.run}
                    className={clsx(
                      'flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors',
                      index === activeIndex ? 'bg-accent-dim text-content' : 'text-content-muted'
                    )}
                  >
                    <span className="shrink-0 text-content-subtle">{command.icon}</span>
                    <span className="min-w-0 flex-1 truncate">{command.label}</span>
                    {command.hint && (
                      <span className="shrink-0 truncate text-2xs text-content-subtle">{command.hint}</span>
                    )}
                    {index === activeIndex && (
                      <CornerDownLeft size={13} className="shrink-0 text-content-subtle" aria-hidden />
                    )}
                  </button>
                </li>
              ))}
            </ul>

            <footer className="flex items-center gap-3 border-t border-line px-4 py-2 text-2xs text-content-subtle">
              <span>
                <span className="kbd">↑</span> <span className="kbd">↓</span> navigate
              </span>
              <span>
                <span className="kbd">↵</span> select
              </span>
              <span>
                <span className="kbd">esc</span> close
              </span>
            </footer>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
};
