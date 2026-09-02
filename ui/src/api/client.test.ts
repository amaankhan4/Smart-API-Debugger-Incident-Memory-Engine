import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';

import { errorMessage } from './client';

const axiosErrorWith = (status: number, data: unknown) => {
  const error = new AxiosError('Request failed');
  error.response = {
    status,
    data,
    statusText: '',
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() }
  };
  return error;
};

describe('errorMessage', () => {
  it('surfaces the API detail string', () => {
    expect(errorMessage(axiosErrorWith(404, { detail: 'Incident not found' }))).toBe(
      'Incident not found'
    );
  });

  it('surfaces the first validation error message', () => {
    const error = axiosErrorWith(422, { detail: [{ msg: 'Password too short' }] });
    expect(errorMessage(error)).toBe('Password too short');
  });

  it('falls back to the status code when detail is unusable', () => {
    expect(errorMessage(axiosErrorWith(500, {}))).toBe('Request failed with status 500');
  });

  it('explains an unreachable backend instead of showing a raw axios error', () => {
    const error = new AxiosError('Network Error');
    expect(errorMessage(error)).toBe('Cannot reach the API. Is the backend running?');
  });

  it('explains a timeout', () => {
    const error = new AxiosError('timeout');
    error.code = 'ECONNABORTED';
    expect(errorMessage(error)).toBe('The request timed out. Please try again.');
  });

  it('handles non-axios errors and unknown values', () => {
    expect(errorMessage(new Error('boom'))).toBe('boom');
    expect(errorMessage(null, 'fallback text')).toBe('fallback text');
  });
});
