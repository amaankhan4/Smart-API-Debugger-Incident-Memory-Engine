import { api } from './client';
import type {
  ClusterRunResponse,
  EventRecord,
  IncidentDetail,
  IncidentRecord,
  IncidentSeverity,
  IncidentStatus,
  Note,
  NoteType,
  Page
} from 'types/api';

export type IncidentFilters = {
  status?: IncidentStatus;
  severity?: IncidentSeverity;
  service?: string;
  search?: string;
  sort?: 'last_seen' | 'first_seen' | 'event_count' | 'created_at' | 'severity';
  order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
};

const clean = (params: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== '' && value !== null)
  );

export const getIncidents = async (params: IncidentFilters = {}) => {
  const { data } = await api.get<Page<IncidentRecord>>('/incidents', { params: clean(params) });
  return data;
};

export const getIncidentDetail = async (incidentId: string) => {
  const { data } = await api.get<IncidentDetail>(`/incidents/${incidentId}`);
  return data;
};

export const getIncidentEvents = async (incidentId: string, limit = 50, offset = 0) => {
  const { data } = await api.get<Page<EventRecord>>(`/incidents/${incidentId}/events`, {
    params: { limit, offset }
  });
  return data;
};

export const updateIncidentStatus = async (
  incidentId: string,
  payload: { status: IncidentStatus; severity?: IncidentSeverity }
) => {
  const { data } = await api.patch<IncidentRecord>(`/incidents/${incidentId}/status`, payload);
  return data;
};

export const getIncidentNotes = async (incidentId: string) => {
  const { data } = await api.get<Page<Note>>(`/incidents/${incidentId}/notes`);
  return data;
};

export const addIncidentNote = async (
  incidentId: string,
  payload: { note: string; type: NoteType; event_id?: string }
) => {
  const { data } = await api.post<Note>(`/incidents/${incidentId}/notes`, payload);
  return data;
};

export const deleteIncidentNote = async (incidentId: string, noteId: string) => {
  const { data } = await api.delete<{ message: string }>(`/incidents/${incidentId}/notes/${noteId}`);
  return data;
};

export const runClustering = async () => {
  const { data } = await api.post<ClusterRunResponse>('/incidents/cluster');
  return data;
};

