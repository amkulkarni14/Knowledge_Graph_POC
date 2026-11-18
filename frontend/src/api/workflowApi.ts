import { api, get, send, sessionPath as p } from "./client";
import type {
  Schema,
  JsonObject,
  Page,
  Job,
  GraphSelection,
} from "../types/common.types";
export const scopeApi = {
  read: (id: string, signal?: AbortSignal) =>
    get<Schema<"ScopeRequest"> | null>(p(id, "/scope"), undefined, signal),
  save: (id: string, body: Schema<"ScopeRequest">) =>
    send<JsonObject>("PUT", p(id, "/scope"), body),
};
export const sourcesApi = {
  read: (id: string, signal?: AbortSignal) =>
    get<JsonObject>(p(id, "/sources"), undefined, signal),
  sample: (id: string) => send<JsonObject>("POST", p(id, "/sources/sample")),
  postgres: (id: string, body: Schema<"PostgresRequest">) =>
    send<JsonObject>("POST", p(id, "/sources/postgres"), body),
  upload: async (
    id: string,
    files: File[],
    onProgress: (n: number) => void,
  ) => {
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    return (
      await api.post<{ data: JsonObject }>(p(id, "/sources/upload"), body, {
        onUploadProgress: (e) =>
          onProgress(e.total ? Math.round((e.loaded / e.total) * 100) : 0),
      })
    ).data.data;
  },
};
export const metadataApi = {
  extract: (id: string) =>
    send<Schema<"SchemaCatalog">>("POST", p(id, "/metadata/extract")),
  catalog: (id: string, signal?: AbortSignal) =>
    get<Schema<"SchemaCatalog">>(p(id, "/metadata"), undefined, signal),
  tables: (id: string, offset: number, signal?: AbortSignal) =>
    get<Page>(p(id, "/metadata/tables"), { offset, limit: 25 }, signal),
  columns: (id: string, table: string, signal?: AbortSignal) =>
    get<JsonObject[]>(p(id, "/metadata/columns"), { table }, signal),
  preview: (id: string, table: string, signal?: AbortSignal) =>
    get<JsonObject[]>(p(id, "/metadata/preview"), { table, limit: 20 }, signal),
  analyze: (id: string) => send<JsonObject>("POST", p(id, "/metadata/analyze")),
  analysis: (id: string, signal?: AbortSignal) =>
    get<JsonObject[]>(p(id, "/metadata/analysis"), undefined, signal),
};
export const ontologyApi = {
  draft: (id: string, signal?: AbortSignal) =>
    get<Schema<"Ontology">>(p(id, "/ontology/draft"), undefined, signal),
  create: (id: string, body: Schema<"DraftRequest">) =>
    send<{ ontology: Schema<"Ontology">; notes: string[] }>(
      "POST",
      p(id, "/ontology/draft"),
      body,
    ),
  replace: (id: string, body: Schema<"OntologyRequest">) =>
    send<Schema<"Ontology">>("PUT", p(id, "/ontology/draft"), body),
  save: (id: string) =>
    send<Schema<"Ontology">>("POST", p(id, "/ontology/draft/save")),
  revert: (id: string) =>
    send<Schema<"Ontology">>("POST", p(id, "/ontology/draft/revert")),
  addClass: (id: string, body: Schema<"ClassRequest">) =>
    send<Schema<"Ontology">>("POST", p(id, "/ontology/classes"), body),
  rename: (id: string, name: string, body: Schema<"RenameRequest">) =>
    send<Schema<"Ontology">>(
      "PATCH",
      p(id, `/ontology/classes/${encodeURIComponent(name)}`),
      body,
    ),
  removeClass: (id: string, name: string) =>
    send<Schema<"Ontology">>(
      "DELETE",
      p(id, `/ontology/classes/${encodeURIComponent(name)}`),
    ),
  attributes: (id: string, name: string, body: Schema<"AttributesRequest">) =>
    send<Schema<"Ontology">>(
      "PUT",
      p(id, `/ontology/classes/${encodeURIComponent(name)}/attributes`),
      body,
    ),
  relationship: (id: string, body: Schema<"RelationshipRequest">) =>
    send<Schema<"Ontology">>("POST", p(id, "/ontology/relationships"), body),
  removeRelationship: (id: string, key: string) =>
    send<Schema<"Ontology">>(
      "DELETE",
      p(id, "/ontology/relationships"),
      undefined,
      { key },
    ),
  suggest: (id: string, body: Schema<"AIRequest">) =>
    send<Schema<"ReviewItem">[]>("POST", p(id, "/ontology/suggestions"), body),
  suggestions: (id: string, signal?: AbortSignal) =>
    get<{ items: Schema<"ReviewItem">[]; metadata: JsonObject }>(
      p(id, "/ontology/suggestions"),
      undefined,
      signal,
    ),
  skip: (id: string) =>
    send<JsonObject>("POST", p(id, "/ontology/suggestions/skip")),
  review: (id: string, body: Schema<"ReviewRequest">, preview = false) =>
    send<Schema<"Ontology">>(
      "POST",
      p(id, `/ontology/review${preview ? "/preview" : ""}`),
      body,
    ),
  validate: (id: string) =>
    send<JsonObject>("POST", p(id, "/ontology/validate")),
  validation: (id: string, signal?: AbortSignal) =>
    get<JsonObject>(p(id, "/ontology/validation"), undefined, signal),
  approve: (id: string, body: Schema<"ApprovalRequest">) =>
    send<Schema<"Ontology">>("POST", p(id, "/ontology/approve"), body),
  versions: (id: string, ontology_id: string, signal?: AbortSignal) =>
    get<JsonObject[]>(p(id, "/ontology/versions"), { ontology_id }, signal),
  version: (
    id: string,
    ontology_id: string,
    version: number,
    signal?: AbortSignal,
  ) =>
    get<Schema<"Ontology">>(
      p(id, `/ontology/versions/${version}`),
      { ontology_id },
      signal,
    ),
  rollback: (id: string, ontology_id: string, version: number, actor: string) =>
    send<Schema<"Ontology">>(
      "POST",
      p(id, `/ontology/versions/${version}/rollback`),
      { actor },
      { ontology_id },
    ),
  useApproved: (id: string, ontology_id: string) =>
    send<Schema<"Ontology">>(
      "POST",
      p(id, "/ontology/use-approved"),
      undefined,
      { ontology_id },
    ),
  audit: (
    id: string,
    ontology_id: string,
    offset: number,
    signal?: AbortSignal,
  ) =>
    get<Page>(
      p(id, "/ontology/audit"),
      { ontology_id, offset, limit: 25 },
      signal,
    ),
};
export const buildsApi = {
  start: (id: string, body: Schema<"BuildRequest">) =>
    send<Job>("POST", p(id, "/builds"), body),
  status: (id: string, signal?: AbortSignal) =>
    get<Job | null>(p(id, "/builds/status"), undefined, signal),
  run: (id: string, stage: number, body: Schema<"BuildRequest">) =>
    send<JsonObject>("POST", p(id, `/builds/stages/${stage}`), body),
  result: (id: string, stage: number, signal?: AbortSignal) =>
    get<JsonObject>(p(id, `/builds/stages/${stage}`), undefined, signal),
  rows: (id: string, table: string, offset: number, signal?: AbortSignal) =>
    get<Page>(
      p(id, "/builds/extracted-rows"),
      { table, offset, limit: 25 },
      signal,
    ),
  cleaning: (id: string, kind: string, offset: number, signal?: AbortSignal) =>
    get<Page>(p(id, `/builds/cleaning/${kind}`), { offset, limit: 25 }, signal),
};
export const graphsApi = {
  data: (
    id: string,
    params: GraphSelection & {
      limit?: number;
      edge_limit?: number;
      labels?: string[];
      focus?: string;
      hops?: number;
    },
    signal?: AbortSignal,
  ) => get<Schema<"GraphView">>(p(id, "/graphs/data"), params, signal),
  nodes: (
    id: string,
    params: GraphSelection & {
      search?: string;
      label?: string;
      offset: number;
      limit: number;
    },
    signal?: AbortSignal,
  ) => get<Page>(p(id, "/graphs/nodes"), params, signal),
  node: (
    id: string,
    params: GraphSelection & { node_id: string },
    signal?: AbortSignal,
  ) => get<JsonObject>(p(id, "/graphs/node"), params, signal),
  path: (
    id: string,
    params: GraphSelection & {
      source: string;
      target: string;
      max_hops: number;
    },
    signal?: AbortSignal,
  ) => get<JsonObject>(p(id, "/graphs/path"), params, signal),
  metrics: (id: string, params: GraphSelection, signal?: AbortSignal) =>
    get<JsonObject>(p(id, "/graphs/metrics"), params, signal),
};
export const snapshotsApi = {
  save: (id: string, body: Schema<"SnapshotRequest">) =>
    send<JsonObject>("POST", p(id, "/graphs/snapshots"), body),
  list: (id: string, ontology_id: string, signal?: AbortSignal) =>
    get<JsonObject[]>(p(id, "/graphs/snapshots"), { ontology_id }, signal),
  promote: (id: string, ontology_id: string, build: string) =>
    send<JsonObject>(
      "POST",
      p(id, `/graphs/snapshots/${encodeURIComponent(build)}/current`),
      undefined,
      { ontology_id },
    ),
  download: async (
    id: string,
    ontology_id: string,
    build: string,
    artifact: string,
  ) => {
    const r = await api.get<Blob>(
      p(
        id,
        `/graphs/snapshots/${encodeURIComponent(build)}/download/${encodeURIComponent(artifact)}`,
      ),
      { params: { ontology_id }, responseType: "blob" },
    );
    return r.data;
  },
};
