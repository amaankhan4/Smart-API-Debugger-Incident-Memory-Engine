import { create } from 'zustand';

type UiState = {
  smartSearch: string;
  setSmartSearch: (value: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  smartSearch: '',
  setSmartSearch: (value) => set({ smartSearch: value })
}));
