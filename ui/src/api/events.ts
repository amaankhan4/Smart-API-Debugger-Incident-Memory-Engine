import { api } from './client';
import type {
  ErrorCategory,
  EventContext,
  EventRecord,
  LogLevel,
  Page,
  SimilarEventMatch
} from 'types/api';

export type EventFilters = {
  file_id?: string;
  service?: string;
  level?: LogLevel;
  error_category?: ErrorCategory;
  incident_id?: string;
  trace_id?: string;
  start_time?: string;
  end_time?: string;
  search?: string;
  only_errors?: boolean;
  limit?: number;
  offset?: number;
};

const clean = (params: EventFilters) =>
  Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== '' && value !== null)
  );

export const getEvents = async (params: EventFilters = {}) => {
  const { data } = await api.get<Page<EventRecord>>('/events', { params: clean(params) });
  return data;
};

export const getEvent = async (eventId: string) => {
  const { data } = await api.get<EventRecord>(`/events/${eventId}`);
  return data;
};

export const getEventContext = async (eventId: string) => {
  const { data } = await api.get<EventContext>(`/events/${eventId}/context`);
  return data;
};

export const getSimilarEvents = async (eventId: string, limit = 10) => {
  const { data } = await api.get<SimilarEventMatch[]>(`/events/${eventId}/similar`, {
    params: { limit }
  });
  return data;
};

