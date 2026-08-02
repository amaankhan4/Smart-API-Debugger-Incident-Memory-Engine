import { Link, NavLink, Outlet } from 'react-router-dom';
import { SmartSearchBar } from 'components/SmartSearchBar';

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/upload', label: 'File Upload' },
  { path: '/logs', label: 'Log Explorer' },
  { path: '/incidents', label: 'Incidents' }
];

export const AppLayout = () => (
  <div className="min-h-screen bg-slate-950 text-slate-100">
    <div className="mx-auto grid max-w-[1400px] grid-cols-12 gap-4 p-4">
      <aside className="card col-span-12 h-fit p-4 md:col-span-3 lg:col-span-2">
        <Link to="/dashboard" className="text-sm font-semibold tracking-wide text-indigo-300">
          Smart API Debugger
        </Link>
        <p className="mt-1 text-xs text-slate-500">Semantic Observability Platform</p>
        <nav className="mt-4 flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm transition ${
                  isActive ? 'bg-indigo-500/20 text-indigo-200' : 'text-slate-300 hover:bg-slate-800'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="col-span-12 space-y-4 md:col-span-9 lg:col-span-10">
        <header className="card sticky top-4 z-10 p-3">
          <SmartSearchBar />
        </header>
        <Outlet />
      </main>
    </div>
  </div>
);
