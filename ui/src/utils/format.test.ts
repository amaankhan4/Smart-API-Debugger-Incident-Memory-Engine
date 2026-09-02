import { describe, expect, it } from 'vitest';

import {
  bytesToReadable,
  formatDate,
  formatDuration,
  formatNumber,
  formatPercent,
  titleCase
} from './format';

describe('formatDate', () => {
  it('renders an em dash for missing or invalid values', () => {
    expect(formatDate(undefined)).toBe('—');
    expect(formatDate(null)).toBe('—');
    expect(formatDate('')).toBe('—');
    expect(formatDate('not-a-date')).toBe('—');
  });

  it('formats a valid ISO timestamp', () => {
    expect(formatDate('2024-05-01T10:00:00Z')).toContain('2024');
  });
});

describe('bytesToReadable', () => {
  it('scales through units', () => {
    expect(bytesToReadable(0)).toBe('0 B');
    expect(bytesToReadable(512)).toBe('512 B');
    expect(bytesToReadable(2048)).toBe('2.0 KB');
    expect(bytesToReadable(5 * 1024 * 1024)).toBe('5.0 MB');
  });

  it('handles missing values', () => {
    expect(bytesToReadable(undefined)).toBe('0 B');
  });
});

describe('formatDuration', () => {
  it('picks a sensible unit', () => {
    expect(formatDuration(250)).toBe('250 ms');
    expect(formatDuration(1500)).toBe('1.5 s');
    expect(formatDuration(65_000)).toBe('1m 5s');
    expect(formatDuration(null)).toBe('—');
  });
});

describe('formatNumber and formatPercent', () => {
  it('formats counts and rates', () => {
    expect(formatNumber(1234567)).toMatch(/1.234.567|1,234,567/);
    expect(formatNumber(undefined)).toBe('0');
    expect(formatPercent(0.1234)).toBe('12.3%');
    expect(formatPercent(0)).toBe('0.0%');
  });
});

describe('titleCase', () => {
  it('humanises enum-style values', () => {
    expect(titleCase('rate_limit')).toBe('Rate Limit');
    expect(titleCase('root-cause')).toBe('Root Cause');
    expect(titleCase(undefined)).toBe('');
  });
});
