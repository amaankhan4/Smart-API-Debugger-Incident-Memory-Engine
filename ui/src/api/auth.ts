import { api } from './client';
import type { TokenResponse, User } from 'types/api';

export const register = async (payload: { email: string; name: string; password: string }) => {
  const { data } = await api.post<TokenResponse>('/auth/register', payload);
  return data;
};

export const login = async (payload: { email: string; password: string }) => {
  const { data } = await api.post<TokenResponse>('/auth/login', payload);
  return data;
};

export const fetchMe = async () => {
  const { data } = await api.get<User>('/auth/me');
  return data;
};
