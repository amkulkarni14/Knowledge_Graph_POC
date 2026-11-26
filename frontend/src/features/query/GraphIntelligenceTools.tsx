import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Alert, Button, MenuItem, TextField } from "@mui/material";
import { Link } from "react-router-dom";
import { api, get, send, sessionPath } from "../../api/client";
import { useSessionStore } from "../../app/store";
import { stageRoutes } from "../../constants/stages.constants";
import { stageNavigation } from "../../constants/stageNavigation";
import { useWorkspace } from "../../shared/hooks/useWorkspace";
import {
  DataTable,
  Feedback,
  Panel,
  Report,
} from "../../shared/ui/WorkspaceUi";
import type { JsonObject, Schema } from "../../types/common.types";
import { saveBlob } from "../build/StoragePage";
import GraphCanvas from "./GraphCanvas";

type Insight = {
  degree_in_sample: number;
  nodes_in_sample: number;
  truncated: boolean;
  link_predictions: JsonObject[];
  recommendations: JsonObject[];
  similar_entities: JsonObject[];
  embedding: number[];
  embedding_method: string;
};
type Answer = {
  answer: string;
  citations: number[];
  evidence: JsonObject[];
  trace?: JsonObject[];
  graph: Schema<"GraphView">;
};

export function IntelligenceTools({
  path,
  published,
}: {
  path: string;
  published: boolean;
}) {
  const [mode, setMode] = useState("structural");
  const [node, setNode] = useState("");
  const [targetLabel, setTargetLabel] = useState("");
  const [question, setQuestion] = useState("");
  const [draft, setDraft] = useState("");
  const [selected, setSelected] = useState<string | JsonObject | null>(null);
  const onSelect = useCallback((id: string) => setSelected(id), []);
  const onEdge = useCallback((item: JsonObject) => setSelected(item), []);
  const insights = useMutation({
    mutationFn: () =>
      get<Insight>(path + "/intelligence", {
        node_id: node.trim(),
        target_label: targetLabel.trim(),
      }),
  });
  const answer = useMutation({
    mutationFn: () =>
      send<Answer>(
        "POST",
        path + (mode === "agent" ? "/investigate" : "/graph-rag"),
        {
          node_id: node.trim(),
          question: question.trim(),
        },
      ),
  });
  const suggest = useMutation({
    mutationFn: () =>
      send<{ cypher: string }>("POST", path + "/query-draft", {
        question: question.trim(),
      }),
    onSuccess: (data) => {
      setDraft(data.cypher);
      run.reset();
    },
  });
  const run = useMutation({
    mutationFn: () =>
      send<{ rows: JsonObject[]; duration_ms: number }>(
        "POST",
        path + "/query",
        { cypher: draft },
      ),
  });
  const exportGraph = useMutation({
    mutationFn: async () => {
      const response = await api.get<Blob>(path + "/graphml/neighborhood", {
        params: { node_id: node.trim() },
        responseType: "blob",
      });
      saveBlob(response.data, "neighborhood.graphml");
    },
  });
  const busy = insights.isPending || answer.isPending || suggest.isPending;
  const requiresNode = mode !== "language";
  const requiresQuestion = mode !== "structural";
  return (
    <div className="section-gap">
      <Panel title="Graph intelligence">
        <form
          className="toolbar"
          onSubmit={(event) => {
            event.preventDefault();
            if (mode === "structural") insights.mutate();
            else if (mode === "language") suggest.mutate();
            else answer.mutate();
          }}
        >
          <TextField
            select
            label="Capability"
            value={mode}
            disabled={busy}
            onChange={(event) => {
              setMode(event.target.value);
              setSelected(null);
              insights.reset();
              answer.reset();
              suggest.reset();
              run.reset();
              setDraft("");
            }}
          >
            <MenuItem value="structural">
              Link prediction, recommendations and embeddings
            </MenuItem>
            <MenuItem value="language" disabled={!published}>
              Natural language to Cypher
            </MenuItem>
            <MenuItem value="rag" disabled={!published}>
              GraphRAG
            </MenuItem>
            <MenuItem value="agent" disabled={!published}>
              Read-only investigation workflow
            </MenuItem>
          </TextField>
          {requiresNode && (
            <TextField
              label="Anchor node ID"
              value={node}
              onChange={(event) => setNode(event.target.value)}
            />
          )}
          {mode === "structural" && (
            <TextField
              label="Target label (optional)"
              value={targetLabel}
              onChange={(event) => setTargetLabel(event.target.value)}
            />
          )}
          {requiresQuestion && (
            <TextField
              label="Question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          )}
          <Button
            type="submit"
            variant="contained"
            disabled={
              busy ||
              (requiresNode && !node.trim()) ||
              (requiresQuestion && !question.trim())
            }
          >
            {mode === "language"
              ? "Draft Cypher"
              : mode === "structural"
                ? "Analyze neighborhood"
                : "Investigate"}
          </Button>
          {requiresNode && (
            <Button
              disabled={!node.trim() || exportGraph.isPending}
              onClick={() => exportGraph.mutate()}
            >
              Export neighborhood GraphML
            </Button>
          )}
        </form>
        <Feedback
          pending={busy || exportGraph.isPending}
          error={
            insights.error ?? answer.error ?? suggest.error ?? exportGraph.error
          }
        />
        {!published && (
          <Alert severity="info">
            The current session supports structural analysis. Select a published
            Neo4j version to use natural-language queries, GraphRAG, or
            investigations.
          </Alert>
        )}
        {mode === "language" && suggest.data && (
          <div className="form-stack mt-4">
            <TextField
              label="Review or edit generated Cypher"
              value={draft}
              multiline
              minRows={3}
              onChange={(event) => {
                setDraft(event.target.value);
                run.reset();
              }}
              helperText="The scoped compiler validates the statement again when you run it."
            />
            <Button
              disabled={!draft.trim() || run.isPending}
              onClick={() => run.mutate()}
            >
              Run reviewed query
            </Button>
            <Feedback pending={run.isPending} error={run.error} />
            {run.data && (
              <>
                <p>
                  {run.data.rows.length} results · {run.data.duration_ms} ms
                </p>
                <DataTable rows={run.data.rows} />
              </>
            )}
          </div>
        )}
      </Panel>
      {mode === "structural" && insights.data && (
        <>
          <Panel title="Candidate links">
            <p className="muted">
              Jaccard score ranks shared neighbors in the retrieved undirected
              neighborhood.
            </p>
            <DataTable rows={insights.data.link_predictions} />
          </Panel>
          <Panel title="Recommended entities">
            <p className="muted">
              Scores average link overlap and structural embedding similarity.
            </p>
            <DataTable rows={insights.data.recommendations} />
          </Panel>
          <Panel title="Structural embedding">
            <p>{insights.data.embedding_method}</p>
            <Report value={insights.data.embedding} />
            <DataTable rows={insights.data.similar_entities} />
            <Button
              onClick={() =>
                saveBlob(
                  new Blob([JSON.stringify(insights.data)], {
                    type: "application/json",
                  }),
                  "graph-intelligence.json",
                )
              }
            >
              Download results
            </Button>
          </Panel>
        </>
      )}
      {(mode === "rag" || mode === "agent") && answer.data && (
        <>
          <Panel title="Answer">
            <p>{answer.data.answer}</p>
            <p>
              Referenced evidence IDs:{" "}
              {answer.data.citations.join(", ") || "None"}
            </p>
            <DataTable rows={answer.data.evidence} />
          </Panel>
          {answer.data.trace && (
            <Panel title="Workflow trace">
              <DataTable rows={answer.data.trace} />
            </Panel>
          )}
          <Panel title="Retrieved graph">
            <div className="graph-frame">
              <GraphCanvas
                graph={answer.data.graph}
                layout="cose"
                onSelect={onSelect}
                onEdge={onEdge}
                fitKey={0}
              />
            </div>
            <Report
              value={
                typeof selected === "string"
                  ? answer.data.graph.nodes.find((item) => item.id === selected)
                  : selected
              }
            />
          </Panel>
        </>
      )}
    </div>
  );
}

export function GraphmlImport() {
  const session = useSessionStore((state) => state.id);
  const { done, session: workspace, workflow } = useWorkspace();
  const gate = workflow.validationOnly ? 8 : 9;
  const ontologyReady = workflow.enabled(gate) && done.includes(gate);
  const requiredStep = workflow.order.find((stage) => stage <= gate && !done.includes(stage));
  const requiredAction = workflow.validationOnly ? "Validate" : "Approve";
  const importStage = requiredStep ? stageNavigation[requiredStep] : undefined;
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [labelKey, setLabelKey] = useState("label");
  const [typeKey, setTypeKey] = useState("type");
  const upload = async (action: "preview" | "publish") => {
    const body = new FormData();
    body.set("file", file!);
    body.set("label_key", labelKey.trim() || "label");
    body.set("relationship_key", typeKey.trim() || "type");
    return send<JsonObject>(
      "POST",
      sessionPath(session!, "/graphs/graphml/" + action),
      body,
    );
  };
  const preview = useMutation({ mutationFn: () => upload("preview") });
  const publish = useMutation({ mutationFn: () => upload("publish") });
  const busy = preview.isPending || publish.isPending;
  return (
    <div className="section-gap">
      <Panel title="GraphML import">
        <p>
          Choose a <code>.graphml</code> file from Storage &amp; Snapshots. The
          import uses the active workflow’s approved ontology.
        </p>
        {!session && (
          <Alert
            severity="info"
            action={
              <Button component={Link} to="/">
                Open a workspace
              </Button>
            }
          >
            Open or create a workspace to preview a GraphML file.
          </Alert>
        )}
        {session && !workspace.isPending && !workflow.query.isPending && !ontologyReady && (
          <Alert
            severity="info"
            action={
              requiredStep &&
              importStage && (
                <Button component={Link} to={stageRoutes[requiredStep]}>
                  Go to {importStage.title}
                </Button>
              )
            }
          >
            You can preview the file now. {requiredAction} an ontology in this workflow
            to publish it.
          </Alert>
        )}
        <div className="form-stack mt-4">
          <label>
            GraphML file{" "}
            <input
              type="file"
              accept=".graphml,application/xml"
              disabled={busy}
              onChange={(event) => {
                const selected = event.target.files?.[0] ?? null;
                const supported =
                  !selected || selected.name.toLowerCase().endsWith(".graphml");
                setFile(supported ? selected : null);
                setFileError(
                  supported
                    ? ""
                    : "Choose graph.graphml from the snapshot. The graph.json and .json.gz files use JSON.",
                );
                if (!supported) event.target.value = "";
                preview.reset();
                publish.reset();
              }}
            />
          </label>
          {fileError && <Alert severity="error">{fileError}</Alert>}
          <TextField
            label="Node label attribute"
            value={labelKey}
            placeholder="label"
            helperText="Use label for exports from this app. A blank field also uses label."
            disabled={busy}
            onChange={(event) => {
              setLabelKey(event.target.value);
              preview.reset();
              publish.reset();
            }}
          />
          <TextField
            label="Relationship type attribute"
            value={typeKey}
            placeholder="type"
            helperText="Use type for exports from this app. A blank field also uses type."
            disabled={busy}
            onChange={(event) => {
              setTypeKey(event.target.value);
              preview.reset();
              publish.reset();
            }}
          />
          <div className="toolbar">
            <Button
              variant="contained"
              disabled={!session || !file || busy || workspace.isPending}
              onClick={() => preview.mutate()}
            >
              {ontologyReady ? "Validate and preview" : "Preview GraphML"}
            </Button>
            <Button
              disabled={
                preview.data?.ontology_validated !== true ||
                busy ||
                !session ||
                !ontologyReady ||
                !!publish.data
              }
              onClick={() => publish.mutate()}
            >
              Stage and publish a new version
            </Button>
            {publish.data && (
              <Button component={Link} to="/published-graphs?view=operations">
                View import progress
              </Button>
            )}
          </div>
          <Feedback pending={busy} error={preview.error ?? publish.error} />
          {preview.data?.ontology_validated === false && (
            <Alert severity="info">
              Structure checked. Preview again after preparing the ontology to
              enable publishing.
            </Alert>
          )}
          {preview.data && <Report value={preview.data} />}
          {publish.data && (
            <Alert severity="success">GraphML publication queued.</Alert>
          )}
        </div>
      </Panel>
    </div>
  );
}
