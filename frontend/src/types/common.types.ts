import type { components } from "./generated/openapi";
export type Schema<K extends keyof components["schemas"]> =
  components["schemas"][K];
export type JsonObject = Record<string, unknown>;
export interface Page<T = JsonObject> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}
export interface Stage {
  no: number;
  key: string;
  title: string;
  part: string;
  icon: string;
}
export interface Job {
  id: string;
  status: "queued" | "running" | "completed" | "blocked" | "failed";
  stage: number | null;
  progress: JsonObject | null;
  error: { code: string; message: string } | null;
}
export type GraphSelection = { ontology_id?: string; build_id?: string };
