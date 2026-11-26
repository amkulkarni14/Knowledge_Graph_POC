import { useRef, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  TextField,
} from "@mui/material";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import { DataTable, Feedback, Panel } from "../../shared/ui/WorkspaceUi";
import { guidedSources, type Connection } from "./guidedSources";

export function SourceAssets({
  candidate,
  active,
  changed,
}: {
  candidate: Connection;
  active: boolean;
  changed: () => void;
}) {
  const { id } = useWorkspace();
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const previewed = useRef("");
  const assets = useData(
    ["source-assets", candidate.id, offset, search],
    (signal) => guidedSources.assets(id, candidate.id, offset, search, signal),
  );
  const preview = useAction(
    (session) =>
      guidedSources.preview(session, candidate.id, previewed.current),
    { invalidate: false },
  );
  const confirm = useAction((session) =>
    guidedSources.select(session, candidate.id, selected),
  );
  const cancel = useAction(
    (session) => guidedSources.cancel(session, candidate.id),
    { invalidate: false },
  );
  const page = assets.data?.items ?? [];
  const busy = preview.isPending || confirm.isPending || cancel.isPending;
  return (
    <Panel title="Data discovery and selection">
      <div className="form-stack">
        <TextField
          label="Search assets"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setOffset(0);
          }}
        />
        <Feedback pending={assets.isFetching} error={assets.error} />
        {!!page.length && (
          <FormControlLabel
            label="Select all on this page"
            control={
              <Checkbox
                disabled={busy}
                checked={page.every(({ id }) => selected.includes(id))}
                onChange={(_, checked) => {
                  const ids = page.map(({ id }) => id);
                  setSelected((current) =>
                    checked
                      ? [...new Set([...current, ...ids])].slice(0, 200)
                      : current.filter((id) => !ids.includes(id)),
                  );
                }}
              />
            }
          />
        )}
        {page.map((asset) => (
          <div className="toolbar" key={asset.id}>
            <FormControlLabel
              label={asset.name}
              control={
                <Checkbox
                  checked={selected.includes(asset.id)}
                  disabled={
                    busy ||
                    (selected.length >= 200 && !selected.includes(asset.id))
                  }
                  onChange={(_, checked) =>
                    setSelected((current) =>
                      checked
                        ? [...current, asset.id]
                        : current.filter((id) => id !== asset.id),
                    )
                  }
                />
              }
            />
            <span className="muted">
              {asset.kind}
              {asset.size_bytes != null
                ? ` · ${(asset.size_bytes / 1024).toFixed(1)} KB`
                : ""}
            </span>
            <Button
              disabled={busy}
              onClick={() => {
                previewed.current = asset.id;
                preview.mutate();
              }}
            >
              Preview {asset.name}
            </Button>
          </div>
        ))}
        {assets.data?.total === 0 && (
          <p className="muted">No matching assets.</p>
        )}
        <div className="toolbar">
          <Button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 25))}
          >
            Previous assets
          </Button>
          <Button
            disabled={offset + 25 >= (assets.data?.total ?? 0)}
            onClick={() => setOffset(offset + 25)}
          >
            More assets
          </Button>
          <span className="muted" aria-live="polite">
            {selected.length} selected
          </span>
        </div>
        <Feedback pending={preview.isPending} error={preview.error} />
        {preview.isSuccess && (
          <div>
            <h3>Preview</h3>
            <DataTable
              rows={preview.data.result.columns.map(
                ({ name, pg_type, original_type }) => ({
                  column: name,
                  type: original_type ?? pg_type,
                }),
              )}
            />
            <DataTable rows={preview.data.result.rows} />
          </div>
        )}
        {active && (
          <Alert severity="info">
            Confirming a new selection clears downstream schema, ontology and
            graph results.
          </Alert>
        )}
        <div className="toolbar">
          <Button
            variant="contained"
            disabled={!selected.length || busy}
            onClick={() => confirm.mutate(undefined, { onSuccess: changed })}
          >
            Confirm selection
          </Button>
          <Button
            disabled={busy}
            onClick={() => cancel.mutate(undefined, { onSuccess: changed })}
          >
            Cancel connection
          </Button>
        </div>
        <Feedback
          pending={confirm.isPending || cancel.isPending}
          error={confirm.error ?? cancel.error}
        />
      </div>
    </Panel>
  );
}
