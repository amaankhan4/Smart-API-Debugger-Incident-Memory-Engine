import { api } from './client';
import type { IncidentDetail, IncidentRecord } from 'types/api';

export const getIncidents = async () => {
  const { data } = await api.get<{ items: IncidentRecord[]; count: number }>('/incidents');
  return data;
};

export const getIncidentDetail = async (incidentId: string) => {
  const { data } = await api.get<IncidentDetail>(`/incidents/${incidentId}`);
  return data;
};

export const addIncidentNote = async (incidentId: string, note: string) => {
  const { data } = await api.post(`/incidents/${incidentId}/notes`, null, { params: { note } });
  return data;
};
