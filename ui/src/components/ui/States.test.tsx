import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AsyncBoundary, EmptyState, ErrorState } from './States';

describe('ErrorState', () => {
  it('shows the message and offers a retry', async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Cannot reach the API" onRetry={onRetry} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Cannot reach the API')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('omits the retry button when no handler is given', () => {
    render(<ErrorState message="Read only failure" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('explains the situation and offers an action', () => {
    render(
      <EmptyState
        title="No incidents yet"
        description="Upload and ingest a log file to start discovering recurring failures."
        action={<button type="button">Upload a log file</button>}
      />
    );

    expect(screen.getByText('No incidents yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload a log file/i })).toBeInTheDocument();
  });
});

describe('AsyncBoundary', () => {
  const children = <div>Loaded content</div>;

  it('shows the loading fallback first', () => {
    render(
      <AsyncBoundary isLoading isError={false} loadingFallback={<div>Loading…</div>}>
        {children}
      </AsyncBoundary>
    );

    expect(screen.getByText('Loading…')).toBeInTheDocument();
    expect(screen.queryByText('Loaded content')).not.toBeInTheDocument();
  });

  it('prefers the error state over content', () => {
    render(
      <AsyncBoundary
        isLoading={false}
        isError
        error="Request failed with status 500"
        loadingFallback={<div>Loading…</div>}
      >
        {children}
      </AsyncBoundary>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('Loaded content')).not.toBeInTheDocument();
  });

  it('shows the empty fallback when there is nothing to render', () => {
    render(
      <AsyncBoundary
        isLoading={false}
        isError={false}
        isEmpty
        emptyFallback={<div>Nothing here yet</div>}
        loadingFallback={<div>Loading…</div>}
      >
        {children}
      </AsyncBoundary>
    );

    expect(screen.getByText('Nothing here yet')).toBeInTheDocument();
  });

  it('renders content once loading succeeds', () => {
    render(
      <AsyncBoundary isLoading={false} isError={false} loadingFallback={<div>Loading…</div>}>
        {children}
      </AsyncBoundary>
    );

    expect(screen.getByText('Loaded content')).toBeInTheDocument();
  });
});
