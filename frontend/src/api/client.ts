import axios, { type InternalAxiosRequestConfig } from "axios";
import { z } from "zod";
import type { JsonObject } from "../types/common.types";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1",
  timeout: 30000,
  paramsSerializer: { indexes: null },
});
// The existing backend locks reads as well as mutations. Queue per session;
// lock-free status/events/session views remain available during background builds.
const tails = new Map<string, Promise<void>>();
const releases = new WeakMap<InternalAxiosRequestConfig, () => void>();
api.interceptors.request.use(async (config) => {
  const match = config.url?.match(/\/sessions\/([^/?]+)([^?]*)/);
  if (!match) return config;
  const [, id, path] = match;
  if (
    config.method === "get" &&
    ["", "/events", "/builds/status"].includes(path)
  )
    return config;
  const previous = tails.get(id) ?? Promise.resolve();
  let unlock!: () => void;
  const current = new Promise<void>((resolve) => {
    unlock = resolve;
  });
  tails.set(id, current);
  const release = () => {
    unlock();
    if (tails.get(id) === current) tails.delete(id);
    releases.delete(config);
  };
  releases.set(config, release);
  await previous;
  if (config.signal?.aborted) {
    release();
    throw new axios.CanceledError("Request cancelled", config);
  }
  return config;
});
export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
    public code = "connection_error",
    public details: JsonObject[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}
const errorSchema = z.object({
  error: z.object({
    message: z.string(),
    code: z.string(),
    details: z.array(z.record(z.string(), z.unknown())).optional(),
  }),
});
api.interceptors.response.use(
  (r) => {
    releases.get(r.config)?.();
    return r;
  },
  async (error: unknown) => {
    if (axios.isAxiosError(error) && error.config)
      releases.get(error.config)?.();
    if (axios.isCancel(error)) return Promise.reject(error);
    if (axios.isAxiosError(error)) {
      let body: unknown = error.response?.data;
      if (body instanceof Blob) {
        try {
          body = JSON.parse(await body.text());
        } catch {
          body = null;
        }
      }
      const parsed = errorSchema.safeParse(body);
      const normalized = parsed.success
        ? new ApiError(
            parsed.data.error.message,
            error.response?.status,
            parsed.data.error.code,
            parsed.data.error.details,
          )
        : new ApiError(
            error.response
              ? "The server could not complete this request."
              : "Cannot reach the API. Check that the backend is running.",
            error.response?.status,
          );
      // Release sensitive request references retained by Axios errors.
      if (error.config) error.config.data = undefined;
      return Promise.reject(normalized);
    }
    return Promise.reject(error);
  },
);
export const sessionPath = (id: string, path = "") =>
  `/sessions/${encodeURIComponent(id)}${path}`;
export async function get<T>(
  path: string,
  params?: object,
  signal?: AbortSignal,
): Promise<T> {
  return (await api.get<{ data: T }>(path, { params, signal })).data.data;
}
export async function send<T>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  data?: unknown,
  params?: object,
): Promise<T> {
  return (await api.request<{ data: T }>({ method, url: path, data, params }))
    .data?.data;
}
