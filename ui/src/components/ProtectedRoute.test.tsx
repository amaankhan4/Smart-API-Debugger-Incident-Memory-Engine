import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { ProtectedRoute, PublicOnlyRoute } from './ProtectedRoute';
import { useAuthStore } from 'store/useAuthStore';

const renderAt = (initialPath: string) =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/overview" element={<div>Overview screen</div>} />
        </Route>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<div>Login screen</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );

describe('route guards', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, status: 'idle' });
  });

  it('waits while the session is being restored', () => {
    useAuthStore.setState({ status: 'loading' });
    renderAt('/overview');

    expect(screen.getByRole('status', { name: /loading session/i })).toBeInTheDocument();
    expect(screen.queryByText('Overview screen')).not.toBeInTheDocument();
  });

  it('redirects an unauthenticated visitor to the login screen', () => {
    useAuthStore.setState({ status: 'unauthenticated' });
    renderAt('/overview');

    expect(screen.getByText('Login screen')).toBeInTheDocument();
  });

  it('lets an authenticated user through', () => {
    useAuthStore.setState({
      status: 'authenticated',
      user: { id: '1', email: 'a@b.com', name: 'A', role: 'user' }
    });
    renderAt('/overview');

    expect(screen.getByText('Overview screen')).toBeInTheDocument();
  });

  it('keeps an authenticated user away from the login screen', () => {
    useAuthStore.setState({
      status: 'authenticated',
      user: { id: '1', email: 'a@b.com', name: 'A', role: 'user' }
    });
    renderAt('/login');

    expect(screen.queryByText('Login screen')).not.toBeInTheDocument();
  });
});
