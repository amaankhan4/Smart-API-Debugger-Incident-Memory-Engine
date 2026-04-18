import { api } from './client';
import type { EventContext, EventRecord, SimilarEventMatch } from 'types/api';

type EventFilters = {
  file_id?: string;
  service?: string;
  level?: string;
  trace_id?: string;
  limit?: number;
};

export const getEvents = async (params: EventFilters = {}) => {
  const { data } = await api.get<{ items: EventRecord[]; count: number }>('/events', { params });
  return data;
};

export const getSimilarEvents = async (query: string, limit = 10) => {
  const { data } = await api.get<{ query: string; matches: SimilarEventMatch[] }>('/events/similar', {
    params: { query, limit }
  });
  return data;
};

export const getEventContext = async (eventId: string) => {
  const { data } = await api.get<EventContext>(`/events/${eventId}/context`);
  return data;
};
