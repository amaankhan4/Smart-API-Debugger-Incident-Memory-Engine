import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuthStore } from 'store/useAuthStore';

const FullPageLoader = () => (
  <div className="flex h-full items-center justify-center" role="status" aria-label="Loading session">
    <div className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-accent" />
  </div>
);

export const ProtectedRoute = () => {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();

  if (status === 'idle' || status === 'loading') return <FullPageLoader />;
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
};

export const PublicOnlyRoute = () => {
  const status = useAuthStore((state) => state.status);

  if (status === 'idle' || status === 'loading') return <FullPageLoader />;
  if (status === 'authenticated') return <Navigate to="/overview" replace />;
  return <Outlet />;
};
