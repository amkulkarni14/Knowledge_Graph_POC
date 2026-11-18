import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSessionStore, useGraphStore } from "../../app/store";
import { sessionsApi } from "../../api/sessionsApi";
import { ApiError } from "../../api/client";
import { prerequisites } from "../../constants/stages.constants";
export const useSession = () => {
  const id = useSessionStore((s) => s.id);
  return useQuery({
    queryKey: ["workspace", id, "session"],
    queryFn: ({ signal }) => sessionsApi.read(id!, signal),
    enabled: !!id,
    refetchInterval: 10000,
    retry: false,
  });
};
export function useWorkspace() {
  const id = useSessionStore((s) => s.id);
  const session = useSession();
  return {
    id: id!,
    session,
    done: session.data?.completed_stages ?? [],
    can: (stage: number) =>
      (prerequisites[stage] ?? []).every((n) =>
        session.data?.completed_stages.includes(n),
      ),
  };
}
export function useAction<T>(
  fn: (id: string) => Promise<T>,
  options?: { invalidate?: boolean },
) {
  const client = useQueryClient();
  const id = useSessionStore((s) => s.id);
  const epoch = useSessionStore((s) => s.epoch);
  return useMutation({
    mutationKey: ["workspace-mutation", id],
    gcTime: 0,
    retry: false,
    onMutate: () => ({ id, epoch }),
    mutationFn: async () => {
      if (!id) throw new Error("Create a workspace first.");
      if (client.isMutating({ mutationKey: ["workspace-mutation", id] }) > 1)
        throw new Error("Wait for the current operation.");
      return { result: await fn(id), epoch, id };
    },
    onSuccess: async (value) => {
      if (value.epoch !== useSessionStore.getState().epoch) return;
      if (options?.invalidate !== false) {
        await client.cancelQueries({ queryKey: ["workspace", value.id] });
        const session = await sessionsApi.read(value.id);
        if (value.epoch !== useSessionStore.getState().epoch) return;
        client.setQueryData(["workspace", value.id, "session"], session);
        await client.resetQueries({
          queryKey: ["workspace", value.id],
          predicate: (q) => q.queryKey[2] !== "session",
        });
      }
    },
    onError: (error, _variables, context) => {
      if (
        error instanceof ApiError &&
        error.code === "session_not_found" &&
        context?.epoch === useSessionStore.getState().epoch
      ) {
        useSessionStore
          .getState()
          .setSession(
            null,
            "Your session has expired. Create a new workspace to continue.",
          );
        useGraphStore.getState().reset();
        client.removeQueries({ queryKey: ["workspace", id] });
      }
    },
  });
}
export function useData<T>(
  name: unknown[],
  fn: (signal: AbortSignal) => Promise<T>,
  enabled = true,
) {
  const id = useSessionStore((s) => s.id);
  return useQuery({
    queryKey: ["workspace", id, ...name],
    queryFn: ({ signal }) => fn(signal),
    enabled: !!id && enabled,
    retry: false,
  });
}
