import { api } from './client';
import type { Analytics, ErrorCategory, LogLevel, SearchMode, SearchResponse } from 'types/api';

export type SearchParams = {
  q: string;
  mode?: SearchMode;
  file_id?: string;
  service?: string;
  level?: LogLevel;
  error_category?: ErrorCategory;
  incident_id?: string;
  limit?: number;
};

export const searchEvents = async (params: SearchParams) => {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== '' && value !== null)
  );
  const { data } = await api.get<SearchResponse>('/search', { params: cleaned });
  return data;
};

export const getAnalytics = async (days = 14) => {
  const { data } = await api.get<Analytics>('/analytics', { params: { days } });
  return data;
};
