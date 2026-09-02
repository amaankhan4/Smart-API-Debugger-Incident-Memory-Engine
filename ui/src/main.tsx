import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';

import { setUnauthorizedHandler } from 'api/client';
import App from './App';
import './index.css';
import { useAuthStore } from 'store/useAuthStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000
    }
  }
});

const Root = () => {
  const restore = useAuthStore((state) => state.restore);
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    restore();
    // A 401 anywhere in the app must end the session exactly once, centrally.
    setUnauthorizedHandler(() => {
      logout();
      queryClient.clear();
    });
  }, [restore, logout]);

  return <App />;
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Root />
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#131822',
              border: '1px solid #1E2534',
              color: '#E7EBF3'
            }
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);

