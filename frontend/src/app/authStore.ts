import { create } from "zustand";

const STORAGE_KEY = "kg.auth";

export type AuthUser = { username: string };
type Stored = { token: string; user: AuthUser };

// sessionStorage keeps the JWT across page refreshes but ends it with the tab.
// Anything readable by page scripts is exposed to XSS, so the token is kept
// short-lived (see ACCESS_TOKEN_EXPIRE_MINUTES on the backend).
function readStored(): Stored | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<Stored>;
    return typeof value.token === "string" && typeof value.user?.username === "string"
      ? { token: value.token, user: value.user }
      : null;
  } catch {
    return null;
  }
}

function writeStored(value: Stored | null) {
  try {
    if (value) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable: the session lasts until reload */
  }
}

const initial = readStored();

// Deliberately free of API imports so the HTTP client can read it without a cycle.
export const useAuthStore = create<{
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  logout: () => void;
}>((set) => ({
  token: initial?.token ?? null,
  user: initial?.user ?? null,
  setAuth: (token, user) => {
    writeStored({ token, user });
    set({ token, user });
  },
  logout: () => {
    writeStored(null);
    set({ token: null, user: null });
  },
}));
