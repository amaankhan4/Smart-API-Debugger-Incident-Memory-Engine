import clsx from 'clsx';
import { motion } from 'framer-motion';
import {
  Activity,
  BarChart3,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  ShieldAlert,
  Terminal,
  X
} from 'lucide-react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { CommandPalette } from 'components/CommandPalette';
import { QuotaBanner } from 'components/QuotaBanner';
import { useAuthStore } from 'store/useAuthStore';
import { useUiStore } from 'store/useUiStore';

const NAV_ITEMS = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/files', label: 'Files', icon: FileText },
  { to: '/logs', label: 'Log Explorer', icon: Terminal },
  { to: '/incidents', label: 'Incidents', icon: ShieldAlert },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 }
];

const SidebarContent = ({ onNavigate }: { onNavigate?: () => void }) => {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-accent/30 bg-accent-dim text-accent-soft">
          <Activity size={16} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">Incident Memory</div>
          <div className="text-2xs text-content-subtle">Semantic observability</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3" aria-label="Primary">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-surface-hover font-medium text-content'
                  : 'text-content-muted hover:bg-surface-hover hover:text-content'
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-accent"
                    transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                  />
                )}
                <Icon size={16} className="shrink-0" aria-hidden />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-line p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface-raised text-xs font-semibold uppercase text-content-muted">
            {user?.name?.[0] ?? user?.email?.[0] ?? '?'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-content">{user?.name ?? 'Engineer'}</div>
            <div className="truncate text-2xs text-content-subtle">{user?.email}</div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="btn-ghost shrink-0 p-1.5"
            title="Log out"
            aria-label="Log out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  );
};

export const AppLayout = () => {
  const location = useLocation();
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);
  const setCommandPaletteOpen = useUiStore((state) => state.setCommandPaletteOpen);

  return (
    <div className="flex h-full bg-canvas">
      <aside className="hidden w-60 shrink-0 border-r border-line bg-surface lg:block">
        <SidebarContent />
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setSidebarOpen(false)}
            aria-hidden
          />
          <motion.aside
            initial={{ x: -240 }}
            animate={{ x: 0 }}
            className="relative h-full w-60 border-r border-line bg-surface"
          >
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="btn-ghost absolute right-2 top-4 p-1.5"
              aria-label="Close navigation"
            >
              <X size={16} />
            </button>
            <SidebarContent onNavigate={() => setSidebarOpen(false)} />
          </motion.aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface/80 px-4 backdrop-blur">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="btn-ghost p-2 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={16} />
          </button>

          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            className="flex w-full max-w-md items-center gap-2.5 rounded-lg border border-line bg-surface-raised px-3 py-1.5 text-sm text-content-subtle transition-colors hover:border-line-strong hover:text-content-muted"
          >
            <Search size={14} aria-hidden />
            <span className="flex-1 text-left">Search logs, incidents, actions…</span>
            <kbd className="kbd hidden sm:inline">Ctrl K</kbd>
          </button>
        </header>

        <QuotaBanner />

        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6"
        >
          <Outlet />
        </motion.main>
      </div>

      <CommandPalette />
    </div>
  );
};

