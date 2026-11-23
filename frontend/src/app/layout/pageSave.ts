import { useEffect, useRef } from "react";

/** Resolves true when it is safe to leave the page, false to stay (e.g. validation failed). */
export type PageSaveHandler = () => Promise<boolean> | boolean;

// Only one routed page is mounted at a time, so a single slot is enough.
export const pageSave: { current: PageSaveHandler | null } = { current: null };

/**
 * Registers the current page's save action with the "Save & Next" footer.
 * Pass null when the page has nothing to save yet. A thrown error also keeps
 * the user on the page; the page shows the error through its own mutation state.
 */
export function usePageSave(handler: PageSaveHandler | null) {
  const latest = useRef(handler);
  useEffect(() => {
    latest.current = handler;
  });
  const active = handler !== null;
  useEffect(() => {
    if (!active) return;
    const run: PageSaveHandler = () => latest.current?.() ?? true;
    pageSave.current = run;
    return () => {
      if (pageSave.current === run) pageSave.current = null;
    };
  }, [active]);
}
