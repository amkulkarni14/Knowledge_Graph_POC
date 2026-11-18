import { useSessionStore } from "../../app/store";
import { useState } from "react";
import {
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  MenuItem,
  Alert,
} from "@mui/material";
import { snapshotsApi, ontologyApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import {
  PageHeader,
  Panel,
  Feedback,
  Report,
  DataTable,
  Confirm,
} from "../../shared/ui/WorkspaceUi";
export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default function StoragePage() {
  const { id, can, done } = useWorkspace();
  const [ontology, setOntology] = useState("");
  const [build, setBuild] = useState("");
  const [neo, setNeo] = useState(false);
  const [artifact, setArtifact] = useState("graph.json.gz");
  const [confirm, setConfirm] = useState<"save" | "promote" | null>(null);
  const draft = useData(
    ["ontology", "draft"],
    (signal) => ontologyApi.draft(id, signal),
    done.includes(5),
  );
  const ontologyId = ontology || draft.data?.ontology_id || "";
  const list = useData(
    ["snapshots", ontologyId],
    (signal) => snapshotsApi.list(id, ontologyId, signal),
    !!ontologyId,
  );
  const save = useAction((sid) => snapshotsApi.save(sid, { load_neo4j: neo }));
  const promote = useAction((sid) =>
    snapshotsApi.promote(sid, ontologyId, build),
  );
  const download = useAction(
    async (sid) => {
      const blob = await snapshotsApi.download(
        sid,
        ontologyId,
        build,
        artifact,
      );
      if (currentWorkspaceId() === sid) saveBlob(blob, artifact);
      return undefined;
    },
    { invalidate: false },
  );
  return (
    <>
      <PageHeader
        eyebrow="16 / GRAPH CONSTRUCTION"
        title="Storage & snapshots"
        description="Persist your validated graph, inspect snapshot history, and download artifacts. Optional Neo4j loading uses server-managed credentials."
      />
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_1.5fr] gap-5">
        <Panel title="Save a snapshot">
          <div className="form-stack">
            <p className="muted">
              Snapshots are saved explicitly after graph validation. A completed
              full build does not automatically create a snapshot.
            </p>
            <FormControlLabel
              control={
                <Checkbox
                  checked={neo}
                  onChange={(e) => setNeo(e.target.checked)}
                />
              }
              label="Also load into configured Neo4j"
            />
            <Button
              variant="contained"
              disabled={!can(16) || save.isPending}
              onClick={() => setConfirm("save")}
            >
              Save validated graph
            </Button>
            {!can(16) && (
              <Alert severity="info">
                Construct and successfully validate the graph first.
              </Alert>
            )}
            <Feedback pending={save.isPending} error={save.error} />
            <Report value={save.data?.result} />
          </div>
        </Panel>
        <Panel title="Snapshot history">
          <TextField
            label="Ontology ID"
            value={ontologyId}
            onChange={(e) => setOntology(e.target.value)}
          />
          <Feedback
            pending={list.isFetching}
            error={list.error}
            onRetry={() => void list.refetch()}
          />
          <DataTable rows={list.data ?? []} />
        </Panel>
      </div>
      <div className="section-gap">
        <Panel title="Snapshot actions">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TextField
              select
              label="Snapshot build ID"
              value={list.data?.some(s=>String(s.build_id)===build)?build:""}
              onChange={(e) => setBuild(e.target.value)}
            >
              <MenuItem value="">Choose snapshot</MenuItem>
              {list.data?.map((s) => (
                <MenuItem key={String(s.build_id)} value={String(s.build_id)}>
                  {String(s.build_id)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Artifact"
              value={artifact}
              onChange={(e) => setArtifact(e.target.value)}
            >
              {[
                "graph.json.gz",
                "graph.graphml",
                "quarantine.json",
                "manifest.json",
              ].map((a) => (
                <MenuItem key={a} value={a}>
                  {a}
                </MenuItem>
              ))}
            </TextField>
            <div className="toolbar">
              <Button
                disabled={!build || download.isPending}
                variant="outlined"
                onClick={() => download.mutate()}
              >
                Download
              </Button>
              <Button
                disabled={!build || promote.isPending}
                onClick={() => setConfirm("promote")}
              >
                Make CURRENT
              </Button>
            </div>
          </div>
          <p className="muted mt-3">
            Exports and detailed reports may contain source data. The backend
            verifies snapshot integrity before serving artifacts or promoting
            CURRENT.
          </p>
          <Feedback
            pending={download.isPending}
            error={download.error || promote.error}
          />
        </Panel>
      </div>
      <Confirm
        open={!!confirm}
        title={
          confirm === "save"
            ? "Save graph snapshot?"
            : "Promote snapshot to CURRENT?"
        }
        pending={save.isPending || promote.isPending}
        onClose={() => setConfirm(null)}
        onConfirm={() => {
          const action = confirm === "save" ? save : promote;
          action.mutate(undefined, { onSuccess: () => setConfirm(null) });
        }}
      >
        <p>
          {confirm === "save"
            ? `Save the validated graph${neo ? " and write it to the server-configured Neo4j database" : ""}.`
            : `Use ${build} as the CURRENT snapshot for ${ontologyId}.`}
        </p>
        <Feedback error={save.error || promote.error} />
      </Confirm>
    </>
  );
}
function currentWorkspaceId() {
  return useSessionStore.getState().id;
}
