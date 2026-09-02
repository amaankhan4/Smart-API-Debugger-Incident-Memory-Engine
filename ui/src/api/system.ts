import { api } from './client';
import type { VectorQuota } from 'types/api';

export const getVectorQuota = async () => {
  const { data } = await api.get<VectorQuota>('/system/quota');
  return data;
};
