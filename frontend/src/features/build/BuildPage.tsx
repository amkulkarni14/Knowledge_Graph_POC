import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  TextField,
  MenuItem,
  Alert,
  Accordion,
  AccordionDetails,
  AccordionSummary,
} from "@mui/material";
import { buildsApi, metadataApi } from "../../api/workflowApi";
import { ChevronDown } from "lucide-react";
import { stageNavigation } from "../../constants/stageNavigation";
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
  Confirm,
} from "../../shared/ui/WorkspaceUi";
import { BuildMonitor, buildStageTitle } from "./BuildMonitor";
import type { Job, Schema } from "../../types/common.types";
function BuildPage() {
  const { stage: stageParam } = useParams();
  const stage = Number(stageParam ?? 10);
  const { id, done, can, session } = useWorkspace();
  const savedConfiguration = session.data?.build_configuration;
  const [batch, setBatch] = useState(5000);
  const [rules, setRules] = useState<Schema<"BuildRequest">["business_rules"]>(
    {},
  );
  const [ruleTable, setRuleTable] = useState("");
  const [column, setColumn] = useState("");
  const [rule, setRule] = useState<"non_negative" | "allowed_values">(
    "non_negative",
  );
  const [values, setValues] = useState("");
  const [table, setTable] = useState("");
  const [kind, setKind] = useState("merges");
  const [offset, setOffset] = useState(0);
  const [confirm, setConfirm] = useState(false);

  const status = useQuery({
    queryKey: ["workspace", id, "build", "status"],
    queryFn: ({ signal }) => buildsApi.status(id, signal),
    refetchInterval: (q) =>
      q.state.data && ["queued", "running", "cancelling", "publishing"].includes(q.state.data.status)
        ? 1500
        : false,
    retry: false,
  });
  const client = useQueryClient();
  const jobStatus = status.data?.status;
  useEffect(() => {
    if (jobStatus && ["completed", "blocked", "failed", "cancelled", "interrupted"].includes(jobStatus))
      void client.invalidateQueries({ queryKey: ["workspace", id, "session"] });
  }, [jobStatus, id, client]);
  const busy =
    ["queued", "running", "cancelling", "publishing"].includes(status.data?.status ?? "");
  const config = {
    batch_size: batch,
    business_rules: Object.keys(rules ?? {}).length ? rules : undefined,
  };
  const start = useAction(async (sid) => {
    const job = await buildsApi.start(sid, config);
    client.setQueryData<Job>(["workspace", sid, "build", "status"], job);
    return job;
  }, { invalidate: false });
  const run = useAction((sid) => buildsApi.run(sid, stage, config));
  const catalog = useData(
    ["catalog"],
    (signal) => metadataApi.catalog(id, signal),
    done.includes(3),
  );
  const rows = useData(
    ["build", "rows", table, offset],
    (signal) => buildsApi.rows(id, table, offset, signal),
    !busy && done.includes(11) && !!table && stage === 11,
  );
  const cleaning = useData(
    ["build", "cleaning", kind, offset],
    (signal) => buildsApi.cleaning(id, kind, offset, signal),
    !busy && done.includes(13) && stage === 13,
  );
  const pipeline = useData(["build", "pipeline"], (signal) => buildsApi.pipeline(id, signal));
  if (!pipeline.data) return <Feedback pending={pipeline.isPending} error={pipeline.error} />;
  const first = pipeline.data.steps[0].stage;
  const definition = pipeline.data.steps.find((item) => item.stage === stage);
  if (!definition) return <Alert severity="error">Choose a pipeline stage from the sidebar.</Alert>;
  const stageName = buildStageTitle(definition, first);
  const validBatch = Number.isInteger(batch) && batch >= 1 && batch <= 100000;
  const disabled = busy || start.isPending || run.isPending || status.isPending || !!status.error;
  const configuration = (
    <Accordion disableGutters variant="outlined">
      <AccordionSummary expandIcon={<ChevronDown size={17} />} id="build-config" aria-controls="build-config-content">
        <strong>Build configuration</strong>
      </AccordionSummary>
      <AccordionDetails>
        <fieldset className="form-stack min-w-0" disabled={disabled}>
              {savedConfiguration && (
                <Button disabled={busy} onClick={() => {
                  setBatch(savedConfiguration.batch_size ?? 5000);
                  setRules(savedConfiguration.business_rules ?? {});
                }}>
                  Restore saved build settings
                </Button>
              )}
              <TextField
                label="Extraction batch size"
                type="number"
                value={batch}
                onChange={(e) => setBatch(Number(e.target.value))}
                slotProps={{ htmlInput: { min: 1, max: 100000 } }}
              />
              <h3>Business rules</h3>
              <TextField
                select
                label="Rule table"
                value={ruleTable}
                onChange={(e) => {
                  setRuleTable(e.target.value);
                  setColumn("");
                }}
              >
                <MenuItem value="">Choose a table</MenuItem>
                {Object.keys(catalog.data?.tables ?? {}).map((t) => (
                  <MenuItem value={t} key={t}>
                    {t}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Column"
                value={column}
                onChange={(e) => setColumn(e.target.value)}
              >
                <MenuItem value="">Choose a column</MenuItem>
                {Object.keys(
                  catalog.data?.tables[ruleTable]?.columns ?? {},
                ).map((c) => (
                  <MenuItem value={c} key={c}>
                    {c}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Rule type"
                value={rule}
                onChange={(e) => setRule(e.target.value as typeof rule)}
              >
                <MenuItem value="non_negative">Non-negative</MenuItem>
                <MenuItem value="allowed_values">Allowed values</MenuItem>
              </TextField>
              {rule === "allowed_values" && (
                <TextField
                  label="Allowed values — comma separated"
                  value={values}
                  onChange={(e) => setValues(e.target.value)}
                />
              )}
              <Button
                disabled={
                  !ruleTable ||
                  !column ||
                  (rule === "allowed_values" && !values.trim())
                }
                onClick={() =>
                  setRules((r) => ({
                    ...r,
                    [ruleTable]: [
                      ...(r?.[ruleTable] ?? []),
                      {
                        column,
                        rule,
                        ...(rule === "allowed_values"
                          ? {
                              values: values
                                .split(",")
                                .map((v) => v.trim())
                                .filter(Boolean),
                            }
                          : {}),
                      },
                    ],
                  }))
                }
              >
                Add rule
              </Button>
              <Report value={rules} />
              {!!Object.keys(rules ?? {}).length && (
                <Button onClick={() => setRules({})}>Clear rules</Button>
              )}
        </fieldset>
      </AccordionDetails>
    </Accordion>
  );
  return (
    <>
      <PageHeader
        eyebrow="Graph Construction"
        title={stage === first ? stageNavigation[stage].title : stageName}
        description="Configure, execute, and monitor the knowledge graph construction pipeline."
        action={<div className="toolbar">
          {stageParam && <Button variant="outlined" disabled={disabled || !can(stage) || !validBatch}
            onClick={() => run.mutate()}>Run {stageName}</Button>}
          <Button variant="contained" disabled={disabled || !can(first) || !validBatch}
            onClick={() => setConfirm(true)}>Build Knowledge Graph</Button>
        </div>}
      />
      <Feedback pending={run.isPending || start.isPending} error={run.error || start.error} />
      <BuildMonitor id={id} pipeline={pipeline.data} job={status.data} busy={busy}
        workspace={session.data} selected={stageParam ? stage : undefined} error={status.error} configuration={configuration}>
        {(activeStage) => <>
      {activeStage === 11 && stage === 11 && !busy && done.includes(11) && (
        <div className="section-gap">
          <Panel title="Extracted rows">
            <TextField
              select
              label="Extracted table"
              value={table}
              onChange={(e) => {
                setTable(e.target.value);
                setOffset(0);
              }}
            >
              <MenuItem value="">Choose a table</MenuItem>
              {Object.keys(catalog.data?.tables ?? {}).map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </TextField>
            <Feedback error={rows.error} />
            <DataTable
              rows={rows.data?.items ?? []}
              offset={offset}
              total={rows.data?.total}
              onPage={setOffset}
            />
          </Panel>
        </div>
      )}
      {activeStage === 13 && stage === 13 && !busy && done.includes(13) && (
        <div className="section-gap">
          <Panel title="Cleaning findings">
            <TextField
              select
              label="Result kind"
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setOffset(0);
              }}
            >
              {["merges", "changes", "quarantine", "records"].map((k) => (
                <MenuItem key={k} value={k}>
                  {k}
                </MenuItem>
              ))}
            </TextField>
            <Feedback error={cleaning.error} />
            <DataTable
              rows={cleaning.data?.items ?? []}
              offset={offset}
              total={cleaning.data?.total}
              onPage={setOffset}
            />
          </Panel>
        </div>
      )}
        </>}
      </BuildMonitor>
      <Confirm open={confirm} title="Build Knowledge Graph?"
        onClose={() => setConfirm(false)}
        onConfirm={() => start.mutate(undefined, { onSuccess: () => setConfirm(false) })}
        pending={start.isPending}>
        <p>Run the pipeline with the current ontology and business rules. Saving a snapshot is a separate action.</p>
        <Feedback error={start.error} />
      </Confirm>
    </>
  );
}

export default function BuildRoute() {
  const { stage } = useParams();
  const { id } = useWorkspace();
  return <BuildPage key={id + "/" + (stage ?? "all")} />;
}
