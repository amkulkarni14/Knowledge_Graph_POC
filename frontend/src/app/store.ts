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
  collapsedGroups: string[];
  scopeDirty: boolean;
  setScopeDirty: (dirty: boolean) => void;
  toggleSidebar: () => void;
  toggleActivity: () => void;
  toggleGroup: (group: string) => void;
}>((set) => ({
  collapsed: false,
  activity: false,
  collapsedGroups: [],
  scopeDirty: false,
  setScopeDirty: (scopeDirty) => set({ scopeDirty }),
  toggleSidebar: () => set((s) => ({ collapsed: !s.collapsed })),
  toggleActivity: () => set((s) => ({ activity: !s.activity })),
  toggleGroup: (group) =>
    set((s) => ({
      collapsedGroups: s.collapsedGroups.includes(group)
        ? s.collapsedGroups.filter((item) => item !== group)
        : [...s.collapsedGroups, group],
    })),
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
