import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { ErrorCategory, LogLevel } from 'types/api';

export type LogFilters = {
  search: string;
  level?: LogLevel;
  service?: string;
  fileId?: string;
  errorCategory?: ErrorCategory;
  onlyErrors: boolean;
};

export const emptyLogFilters: LogFilters = {
  search: '',
  level: undefined,
  service: undefined,
  fileId: undefined,
  errorCategory: undefined,
  onlyErrors: false
};

type UiState = {
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;

  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;

  logFilters: LogFilters;
  setLogFilters: (patch: Partial<LogFilters>) => void;
  resetLogFilters: () => void;
};

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      toggleCommandPalette: () => set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

      sidebarOpen: false,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      logFilters: emptyLogFilters,
      setLogFilters: (patch) => set((state) => ({ logFilters: { ...state.logFilters, ...patch } })),
      resetLogFilters: () => set({ logFilters: emptyLogFilters })
    }),
    {
      name: 'ime.ui',
      // Only investigation filters are worth surviving a reload; transient UI is not.
      partialize: (state) => ({ logFilters: state.logFilters })
    }
  )
);

