import { useState, type ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, it, expect, vi } from "vitest";
import { useAction } from "../shared/hooks/useWorkspace";
import { useSessionStore } from "../app/store";
import { sessionsApi } from "../api/sessionsApi";
import { ApiError } from "../api/client";
let client: QueryClient;
function Wrapper({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => {
    client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    return client;
  });
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
describe("workspace mutations", () => {
  beforeEach(() => useSessionStore.getState().setSession("first"));
  it("ignores responses belonging to a replaced session", async () => {
    let complete!: (value: string) => void;
    const read = vi.spyOn(sessionsApi, "read");
    const { result } = renderHook(
      () =>
        useAction(
          () =>
            new Promise<string>((r) => {
              complete = r;
            }),
        ),
      { wrapper: Wrapper },
    );
    act(() => result.current.mutate());
    await waitFor(() => expect(result.current.isPending).toBe(true));
    act(() => useSessionStore.getState().setSession("second"));
    await act(async () => complete("old result"));
    await waitFor(() => expect(result.current.isPending).toBe(false));
    expect(read).not.toHaveBeenCalled();
    expect(useSessionStore.getState().id).toBe("second");
  });
  it("clears expired sessions without retrying the mutation", async () => {
    const fn = vi
      .fn()
      .mockRejectedValue(
        new ApiError("Session has expired", 404, "session_not_found"),
      );
    const { result } = renderHook(() => useAction(fn), { wrapper: Wrapper });
    act(() => result.current.mutate());
    await waitFor(() => expect(useSessionStore.getState().id).toBeNull());
    expect(useSessionStore.getState().id).toBeNull();
    expect(fn).toHaveBeenCalledTimes(1);
  });
  it("refreshes authoritative completion and removes stale derived query data", async () => {
    vi.spyOn(sessionsApi, "read").mockResolvedValue({
      id: "first",
      name: "First",
      completed_stages: [1, 2],
      source_version: 2,
      expires_in_seconds: 3600,
      job: null,
    });
    const { result } = renderHook(
      () => useAction(async () => ({ changed: true })),
      { wrapper: Wrapper },
    );
    client.setQueryData(["workspace", "first", "ontology", "draft"], {
      name: "Old draft",
    });
    act(() => result.current.mutate());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(
      client.getQueryData(["workspace", "first", "session"]),
    ).toMatchObject({ completed_stages: [1, 2] });
    expect(
      client.getQueryData(["workspace", "first", "ontology", "draft"]),
    ).toBeUndefined();
  });
  it("does not mutate without an active workspace", async () => {
    useSessionStore.getState().setSession(null);
    const fn = vi.fn();
    const { result } = renderHook(() => useAction(fn), { wrapper: Wrapper });
    act(() => result.current.mutate());
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fn).not.toHaveBeenCalled();
  });
});
