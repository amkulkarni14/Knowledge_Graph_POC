import { get, send, sessionPath } from "./client";
import type { Schema, Stage, Page } from "../types/common.types";
export const sessionsApi = {
  create: (body: Schema<"SessionCreate">) =>
    send<Schema<"SessionView">>("POST", "/sessions", body),
  read: (id: string, signal?: AbortSignal) =>
    get<Schema<"SessionView">>(sessionPath(id), undefined, signal),
  remove: (id: string) => send<void>("DELETE", sessionPath(id)),
  stages: (signal?: AbortSignal) => get<Stage[]>("/stages", undefined, signal),
  health: (signal?: AbortSignal) =>
    get<Record<string, unknown>>("/health", undefined, signal),
  events: (id: string, offset = 0, signal?: AbortSignal) =>
    get<Page>(sessionPath(id, "/events"), { offset, limit: 100 }, signal),
};
