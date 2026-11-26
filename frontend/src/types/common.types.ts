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
  prerequisites?: number[];
}
export interface Job {
  id: string;
  status: "queued" | "running" | "cancelling" | "publishing" | "completed" | "blocked" | "failed" | "cancelled" | "interrupted";
  stage: number | null;
  progress: JsonObject | null;
  error: { code: string; message: string } | null;
  started_at?: string;
  finished_at?: string;
  steps?: BuildStep[];
  events?: BuildEvent[];
}
export interface BuildStep {
  stage: number;
  status: "pending" | "running" | "completed" | "failed" | "skipped" | "interrupted";
  duration_ms?: number;
  result?: JsonObject;
}
export interface BuildEvent {
  time: string;
  stage: number | null;
  severity: "info" | "success" | "warning" | "error";
  message: string;
}
export interface BuildStage {
  stage: number;
  title: string;
}
export interface BuildPipeline {
  steps: BuildStage[];
  persistence: BuildStage;
}
export type GraphSelection = { ontology_id?: string; build_id?: string };
