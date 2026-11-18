import { useState } from "react";
import { Button, MenuItem, TextField } from "@mui/material";
import { metadataApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import {
  DataTable,
  Feedback,
  PageHeader,
  Panel,
  Report,
} from "../../shared/ui/WorkspaceUi";
export default function MetadataPage({
  analysis = false,
}: {
  analysis?: boolean;
}) {
  const { id, can, done } = useWorkspace();
  const [table, setTable] = useState("");
  const [offset, setOffset] = useState(0);
  const extract = useAction((sid) => metadataApi.extract(sid));
  const analyze = useAction((sid) => metadataApi.analyze(sid));
  const catalog = useData(
    ["catalog"],
    (signal) => metadataApi.catalog(id, signal),
    done.includes(3),
  );
  const tables = useData(
    ["tables", offset],
    (signal) => metadataApi.tables(id, offset, signal),
    done.includes(3),
  );
  const selected = table || Object.keys(catalog.data?.tables ?? {})[0] || "";
  const columns = useData(
    ["columns", selected],
    (signal) => metadataApi.columns(id, selected, signal),
    !!selected,
  );
  const preview = useData(
    ["preview", selected],
    (signal) => metadataApi.preview(id, selected, signal),
    !!selected,
  );
  const result = useData(
    ["analysis"],
    (signal) => metadataApi.analysis(id, signal),
    done.includes(4),
  );
  return (
    <>
      <PageHeader
        eyebrow={`${analysis ? "04" : "03"} / DATA & METADATA`}
        title={analysis ? "Understand your schema" : "Explore source metadata"}
        description={
          analysis
            ? "Inspect table classifications and candidate relationships before drafting an ontology."
            : "Extract the schema, inspect keys and columns, and preview bounded source rows."
        }
        action={
          <Button
            variant="contained"
            disabled={
              !can(analysis ? 4 : 3) || (analysis ? analyze : extract).isPending
            }
            onClick={() => (analysis ? analyze.mutate() : extract.mutate())}
          >
            {analysis ? "Analyze metadata" : "Extract metadata"}
          </Button>
        }
      />
      <Feedback
        pending={extract.isPending || analyze.isPending}
        error={extract.error || analyze.error}
      />
      {analysis ? (
        <>
          <Panel title="Table classifications">
            <Feedback error={result.error} />
            <DataTable rows={result.data ?? []} />
          </Panel>
          {analyze.data && (
            <div className="section-gap">
              <Panel title="Latest analysis and relationship candidates">
                <Report value={analyze.data.result} />
              </Panel>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col gap-5">
          <Panel title="Source tables">
            <Feedback
              pending={tables.isFetching}
              error={tables.error}
              onRetry={() => void tables.refetch()}
            />
            <DataTable
              rows={tables.data?.items ?? []}
              offset={offset}
              total={tables.data?.total}
              onPage={setOffset}
            />
          </Panel>
          <Panel title="Table inspector">
            <TextField
              label="Qualified table"
              select
              value={selected}
              onChange={(e) => setTable(e.target.value)}
              disabled={!selected}
            >
              {Object.keys(catalog.data?.tables ?? {}).map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </TextField>
            <div className="section-gap">
              <h3 className="mb-3">Columns and types</h3>
              <Feedback error={columns.error} />
              <DataTable rows={columns.data ?? []} />
            </div>
            <div className="section-gap">
              <h3 className="mb-3">Row preview</h3>
              <p className="muted mb-3">
                Up to 20 rows. Configured sensitive columns are omitted by the
                backend.
              </p>
              <Feedback error={preview.error} />
              <DataTable rows={preview.data ?? []} />
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
