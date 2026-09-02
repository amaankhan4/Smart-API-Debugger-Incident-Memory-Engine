import { create } from 'zustand';

import { fetchMe, login as loginRequest, register as registerRequest } from 'api/auth';
import { tokenStorage } from 'api/client';
import type { User } from 'types/api';

type AuthState = {
  user: User | null;
  status: 'idle' | 'loading' | 'authenticated' | 'unauthenticated';
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  restore: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: 'idle',

  login: async (email, password) => {
    const data = await loginRequest({ email, password });
    tokenStorage.set(data.access_token);
    set({ user: data.user, status: 'authenticated' });
  },

  register: async (email, name, password) => {
    const data = await registerRequest({ email, name, password });
    tokenStorage.set(data.access_token);
    set({ user: data.user, status: 'authenticated' });
  },

  logout: () => {
    tokenStorage.clear();
    set({ user: null, status: 'unauthenticated' });
  },

  restore: async () => {
    if (!tokenStorage.get()) {
      set({ user: null, status: 'unauthenticated' });
      return;
    }
    set({ status: 'loading' });
    try {
      // A stored token is only trusted after the server confirms it.
      const user = await fetchMe();
      set({ user, status: 'authenticated' });
    } catch {
      tokenStorage.clear();
      set({ user: null, status: 'unauthenticated' });
    }
  }
}));
