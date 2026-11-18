import { useState } from "react";
import {
  Button,
  TextField,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Alert,
} from "@mui/material";
import { ontologyApi, metadataApi } from "../../api/workflowApi";
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
  StatusChip,
} from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
export default function ReviewPages({ mode }: { mode: string }) {
  const { id, done, can } = useWorkspace();
  const [actor, setActor] = useState("data.modeller");
  const [reviewer, setReviewer] = useState("");
  const [live, setLive] = useState(false);
  const [samples, setSamples] = useState(false);
  const [allowed, setAllowed] = useState<string[]>([]);
  const [restrict, setRestrict] = useState(false);
  const [decisions, setDecisions] = useState<
    Record<string, { action: "approve" | "edit" | "reject"; text: string }>
  >({});
  const [acyclic, setAcyclic] = useState("");
  const [watermark, setWatermark] = useState("");
  const [ontologyId, setOntologyId] = useState("retail");
  const [version, setVersion] = useState(1);
  const [offset, setOffset] = useState(0);
  const [confirm, setConfirm] = useState<"approve" | "rollback" | null>(null);
  const catalog = useData(
    ["catalog"],
    (signal) => metadataApi.catalog(id, signal),
    done.includes(3),
  );
  const draft = useData(
    ["ontology", "draft"],
    (signal) => ontologyApi.draft(id, signal),
    done.includes(5),
  );
  const suggestions = useData(
    ["ontology", "suggestions"],
    (signal) => ontologyApi.suggestions(id, signal),
    done.includes(6),
  );
  const validation = useData(
    ["ontology", "validation"],
    (signal) => ontologyApi.validation(id, signal),
    done.includes(7) && mode === "validation",
  );
  const versions = useData(
    ["ontology", "versions", ontologyId],
    (signal) => ontologyApi.versions(id, ontologyId, signal),
    mode === "repository" && !!ontologyId,
  );
  const audit = useData(
    ["ontology", "audit", ontologyId, offset],
    (signal) => ontologyApi.audit(id, ontologyId, offset, signal),
    mode === "repository" && !!ontologyId,
  );
  const versionData = useData(
    ["ontology", "version", ontologyId, version],
    (signal) => ontologyApi.version(id, ontologyId, version, signal),
    mode === "repository" &&
      !!versions.data?.some((v) => Number(v.version) === version),
  );
  const generate = useAction((sid) =>
    ontologyApi.suggest(sid, {
      actor,
      use_groq: live,
      include_samples: samples,
      allowed_tables: restrict ? allowed : undefined,
    }),
  );
  const skip = useAction((sid) => ontologyApi.skip(sid));
  function body(): Schema<"ReviewRequest"> {
    return {
      actor,
      decisions: Object.fromEntries(
        Object.entries(decisions).map(([key, d]) => [
          key,
          d.action === "edit"
            ? {
                action: "edit" as const,
                payload: JSON.parse(d.text) as Record<string, unknown>,
              }
            : { action: d.action },
        ]),
      ),
      acyclic_relationships: acyclic
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean),
      watermark_column: watermark || null,
    };
  }
  const preview = useAction((sid) => ontologyApi.review(sid, body(), true), {
    invalidate: false,
  });
  const review = useAction((sid) => ontologyApi.review(sid, body()));
  const validate = useAction((sid) => ontologyApi.validate(sid));
  const approve = useAction((sid) =>
    ontologyApi.approve(sid, { author: actor, reviewer }),
  );
  const rollback = useAction((sid) =>
    ontologyApi.rollback(sid, ontologyId, version, actor),
  );
  const reuse = useAction((sid) => ontologyApi.useApproved(sid, ontologyId));
  const titles: Record<string, [string, string, string]> = {
    suggestions: [
      "06",
      "AI suggestions",
      "Generate suggestions for human review, or explicitly continue without AI.",
    ],
    review: [
      "07",
      "Review the ontology",
      "Decide on suggestions, preview the result, and apply cycle and watermark rules.",
    ],
    validation: [
      "08",
      "Validate the ontology",
      "Inspect structural and semantic findings. Blocking results prevent approval.",
    ],
    repository: [
      "09",
      "Ontology repository",
      "Approve a reviewed ontology, inspect versions and audit history, or create a rollback draft.",
    ],
  };
  const [number, title, description] = titles[mode];
  return (
    <>
      <PageHeader
        eyebrow={`${number} / ONTOLOGY ENGINEERING`}
        title={title}
        description={description}
      />
      {mode === "suggestions" && (
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_1.4fr] gap-5">
          <Panel title="Suggestion options">
            <div className="form-stack">
              <TextField
                label="Actor"
                value={actor}
                onChange={(e) => setActor(e.target.value)}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={live}
                    onChange={(e) => setLive(e.target.checked)}
                  />
                }
                label="Use live Groq provider"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={samples}
                    onChange={(e) => setSamples(e.target.checked)}
                  />
                }
                label="Include masked sample rows"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={restrict}
                    onChange={(e) => setRestrict(e.target.checked)}
                  />
                }
                label="Restrict to selected tables"
              />
              {restrict && (
                <TextField
                  select
                  label="Allowed tables"
                  slotProps={{ select: { multiple: true } }}
                  value={allowed}
                  onChange={(e) =>
                    setAllowed(
                      typeof e.target.value === "string"
                        ? e.target.value.split(",")
                        : e.target.value,
                    )
                  }
                >
                  {Object.keys(catalog.data?.tables ?? {}).map((t) => (
                    <MenuItem value={t} key={t}>
                      {t}
                    </MenuItem>
                  ))}
                </TextField>
              )}
              <p className="muted">
                Offline suggestions are recorded for the retail sample. Skip AI
                for uploaded data unless the live provider is configured. Live
                requests send selected context to the configured provider.
              </p>
              <Button
                variant="contained"
                disabled={
                  !can(6) ||
                  !actor ||
                  generate.isPending ||
                  (restrict && !allowed.length)
                }
                onClick={() => generate.mutate()}
              >
                Generate suggestions
              </Button>
              <Button
                variant="outlined"
                disabled={!can(6) || skip.isPending}
                onClick={() => skip.mutate()}
              >
                Skip AI suggestions
              </Button>
              <Feedback
                pending={generate.isPending || skip.isPending}
                error={generate.error || skip.error}
              />
            </div>
          </Panel>
          <Panel title="Suggestions and provenance">
            <Feedback error={suggestions.error} />
            <DataTable
              rows={(suggestions.data?.items ?? []).map((i) => ({ ...i }))}
            />
            <Report value={suggestions.data?.metadata} />
          </Panel>
        </div>
      )}
      {mode === "review" && (
        <div className="flex flex-col gap-5">
          <Panel title="Review decisions">
            {!can(7) && (
              <Alert severity="info">
                Save the manual draft, then generate or skip suggestions.
              </Alert>
            )}
            {suggestions.data?.items
              .filter((i) => i.kind !== "duplicate")
              .map((item) => (
                <div className="panel mb-4" key={item.item_id}>
                  <div className="toolbar mb-3">
                    <h3 className="grow">{item.label}</h3>
                    <StatusChip done={item.status === "valid"}>
                      {item.status}
                    </StatusChip>
                    <span className="muted">
                      Confidence {item.confidence.toFixed(2)}
                    </span>
                  </div>
                  <p className="muted mb-3">{item.rationale}</p>
                  {item.problems?.length > 0 && (
                    <Alert severity="warning">{item.problems.join("; ")}</Alert>
                  )}
                  <TextField
                    select
                    label={`Decision for ${item.label}`}
                    value={decisions[item.item_id]?.action ?? ""}
                    onChange={(e) =>
                      setDecisions((d) => ({
                        ...d,
                        [item.item_id]: {
                          action: e.target.value as
                            "approve" | "edit" | "reject",
                          text: JSON.stringify(item.payload, null, 2),
                        },
                      }))
                    }
                  >
                    <MenuItem value="">No explicit decision</MenuItem>
                    {item.status !== "invalid" && (
                      <MenuItem value="approve">Approve</MenuItem>
                    )}
                    <MenuItem value="edit">Edit and accept</MenuItem>
                    <MenuItem value="reject">Reject</MenuItem>
                  </TextField>
                  {decisions[item.item_id]?.action === "edit" && (
                    <TextField
                      className="mt-4"
                      label={`Edited payload for ${item.label}`}
                      multiline
                      minRows={5}
                      value={decisions[item.item_id].text}
                      onChange={(e) =>
                        setDecisions((d) => ({
                          ...d,
                          [item.item_id]: {
                            ...d[item.item_id],
                            text: e.target.value,
                          },
                        }))
                      }
                    />
                  )}
                </div>
              ))}
            {!suggestions.data?.items.length && (
              <p className="muted">
                There are no suggestions. The manual draft can proceed through
                explicit review.
              </p>
            )}
            {suggestions.data?.items.some((i) => i.kind === "duplicate") && (
              <details>
                <summary>Informational duplicate suggestions</summary>
                <DataTable
                  rows={suggestions.data.items
                    .filter((i) => i.kind === "duplicate")
                    .map((i) => ({ ...i }))}
                />
              </details>
            )}
          </Panel>
          <Panel title="Review rules">
            <div className="form-stack">
              <TextField
                label="Reviewed draft author / actor"
                value={actor}
                onChange={(e) => setActor(e.target.value)}
              />
              <TextField
                label="Acyclic relationship keys — one per line"
                value={acyclic}
                multiline
                minRows={2}
                onChange={(e) => setAcyclic(e.target.value)}
                helperText="Use the full key, e.g. Customer-[REFERRED]->Customer"
              />
              <TextField
                label="Watermark column (optional)"
                value={watermark}
                onChange={(e) => setWatermark(e.target.value)}
              />
              <div className="toolbar">
                <Button
                  variant="outlined"
                  disabled={!can(7) || preview.isPending}
                  onClick={() => preview.mutate()}
                >
                  Preview review
                </Button>
                <Button
                  variant="contained"
                  disabled={!can(7) || review.isPending || !actor}
                  onClick={() => review.mutate()}
                >
                  Apply review
                </Button>
              </div>
              <Feedback
                pending={preview.isPending || review.isPending}
                error={preview.error || review.error}
              />
              {review.isSuccess && (
                <Alert severity="success">
                  Review applied. Continue to ontology validation.
                </Alert>
              )}
              {preview.data && <Report value={preview.data.result} />}
            </div>
          </Panel>
        </div>
      )}
      {mode === "validation" && (
        <Panel
          title="Validation report"
          action={
            <Button
              variant="contained"
              disabled={!can(8) || validate.isPending}
              onClick={() => validate.mutate()}
            >
              Validate ontology
            </Button>
          }
        >
          <Feedback
            pending={validate.isPending || validation.isFetching}
            error={validate.error}
          />
          <Report value={validate.data?.result ?? validation.data} />
          {validation.error && !validate.data && (
            <p className="muted">Run validation to generate a report.</p>
          )}
        </Panel>
      )}
      {mode === "repository" && (
        <div className="flex flex-col gap-5">
          <Panel title="Explicit approval">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <TextField
                label="Reviewed draft author"
                value={actor}
                onChange={(e) => setActor(e.target.value)}
                helperText={`Manual draft author: ${draft.data?.created_by ?? "not available"}`}
              />
              <TextField
                label="Independent reviewer"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
              />
              <Button
                variant="contained"
                disabled={
                  !can(9) ||
                  !actor ||
                  !reviewer ||
                  actor.trim().toLowerCase() === reviewer.trim().toLowerCase()
                }
                onClick={() => setConfirm("approve")}
              >
                Approve ontology
              </Button>
            </div>
            <p className="muted mt-3">
              The author must match the reviewed draft. Author and reviewer are
              workflow labels, not authenticated identities.
            </p>
            <Feedback error={approve.error} />
          </Panel>
          <Panel title="Versions and reuse">
            <div className="toolbar mb-4">
              <TextField
                label="Ontology ID"
                value={ontologyId}
                onChange={(e) => {
                  setOntologyId(e.target.value);
                  setOffset(0);
                }}
              />
              <Button
                disabled={!done.includes(3) || reuse.isPending}
                onClick={() => reuse.mutate()}
              >
                Use approved version
              </Button>
            </div>
            <Feedback error={versions.error || reuse.error} />
            <DataTable rows={versions.data ?? []} />
            <div className="toolbar mt-5">
              <TextField
                label="Version to inspect"
                type="number"
                value={version}
                onChange={(e) => setVersion(Number(e.target.value))}
                slotProps={{ htmlInput: { min: 1 } }}
              />
              <Button
                disabled={!versionData.data || !can(5)}
                onClick={() => setConfirm("rollback")}
              >
                Create rollback draft
              </Button>
            </div>
            <Report value={versionData.data} />
          </Panel>
          <Panel title="Audit history">
            <Feedback error={audit.error} />
            <DataTable
              rows={audit.data?.items ?? []}
              offset={offset}
              total={audit.data?.total}
              onPage={setOffset}
            />
          </Panel>
        </div>
      )}
      <Confirm
        open={!!confirm}
        title={
          confirm === "approve"
            ? "Approve this ontology?"
            : "Create a rollback draft?"
        }
        pending={approve.isPending || rollback.isPending}
        onClose={() => setConfirm(null)}
        onConfirm={() => {
          const action = confirm === "approve" ? approve : rollback;
          action.mutate(undefined, { onSuccess: () => setConfirm(null) });
        }}
      >
        <p>
          {confirm === "approve"
            ? "Confirm that the reviewed and validated ontology is ready for graph construction."
            : "This creates an editable draft from the selected version. The approved version remains in history."}
        </p>
        <Feedback error={approve.error || rollback.error} />
      </Confirm>
    </>
  );
}
