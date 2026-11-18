import { create } from "zustand";
export const useSessionStore = create<{
  id: string | null;
  epoch: number;
  notice: string | null;
  setSession: (id: string | null, notice?: string) => void;
}>((set) => ({
  id: null,
  epoch: 0,
  notice: null,
  setSession: (id, notice) =>
    set((s) => ({ id, epoch: s.epoch + 1, notice: notice ?? null })),
}));
export const useUiStore = create<{
  collapsed: boolean;
  activity: boolean;
  toggleSidebar: () => void;
  toggleActivity: () => void;
}>((set) => ({
  collapsed: false,
  activity: false,
  toggleSidebar: () => set((s) => ({ collapsed: !s.collapsed })),
  toggleActivity: () => set((s) => ({ activity: !s.activity })),
}));
export const useGraphStore = create<{
  selected: string | null;
  layout: string;
  select: (id: string | null) => void;
  setLayout: (layout: string) => void;
  reset: () => void;
}>((set) => ({
  selected: null,
  layout: "cose",
  select: (selected) => set({ selected }),
  setLayout: (layout) => set({ layout }),
  reset: () => set({ selected: null, layout: "cose" }),
}));
