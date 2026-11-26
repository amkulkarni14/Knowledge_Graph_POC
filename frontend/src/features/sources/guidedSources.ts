import { api, get, send, sessionPath } from "../../api/client";
import type { Page, Schema } from "../../types/common.types";

export type Connection = Schema<"ConnectionView">;
export type ConnectionRequest = Schema<"ConnectionRequest">;
export type ConnectorId = ConnectionRequest["source"];
export type ConnectorSpec = Schema<"ConnectorSpec">;
export const labels: Record<ConnectorId, string> = {
  sample: "Built-in Retail Sample",
  csv: "Upload Files",
  postgres: "PostgreSQL",
  mssql: "Microsoft SQL Server",
  oracle: "Oracle Database",
  s3: "Amazon S3",
  azure_blob: "Azure Blob Storage",
  azure_adls: "Azure Data Lake Storage Gen2",
  gcs: "Google Cloud Storage",
  bigquery: "Google BigQuery",
};

const root = (session: string) => sessionPath(session, "/sources");
const connection = (session: string, id: string) =>
  `${root(session)}/connections/${id}`;
export const guidedSources = {
  types: (signal: AbortSignal) =>
    get<Record<ConnectorId, ConnectorSpec>>("/source-types", undefined, signal),
  candidate: (session: string, signal: AbortSignal) =>
    get<Connection | null>(
      `${root(session)}/connections/candidate`,
      undefined,
      signal,
    ),
  test: (session: string, request: ConnectionRequest) =>
    send<Connection>("POST", `${root(session)}/test`, request),
  locations: (session: string, request: ConnectionRequest) =>
    send<string[]>("POST", `${root(session)}/locations`, request),
  connect: (session: string, request: ConnectionRequest) =>
    send<Connection>("POST", `${root(session)}/connections`, request),
  assets: (
    session: string,
    id: string,
    offset: number,
    search: string,
    signal: AbortSignal,
  ) =>
    get<Page<Schema<"AssetView">>>(
      `${connection(session, id)}/assets`,
      { offset, search },
      signal,
    ),
  preview: (session: string, id: string, asset: string) =>
    send<Schema<"PreviewView">>("POST", `${connection(session, id)}/preview`, {
      asset,
    }),
  select: (session: string, id: string, assets: string[]) =>
    send<Connection>("POST", `${connection(session, id)}/select`, { assets }),
  cancel: (session: string, id: string) => api.delete(connection(session, id)),
  disconnect: (session: string) => api.delete(root(session)),
  upload: async (
    session: string,
    files: File[],
    setProgress: (value: number) => void,
  ) => {
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    const response = await api.post<{ data: Connection }>(
      `${root(session)}/connections/upload`,
      body,
      {
        onUploadProgress: ({ loaded, total }) =>
          setProgress(total ? Math.round((loaded / total) * 100) : 0),
      },
    );
    return response.data.data;
  },
};
