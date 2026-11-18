import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  TextField,
  MenuItem,
  Alert,
  LinearProgress,
} from "@mui/material";
import { buildsApi, metadataApi } from "../../api/workflowApi";
import { sessionsApi } from "../../api/sessionsApi";
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
  StatusChip,
} from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
const titles: Record<number, string> = {
  10: "Build planning",
  11: "Data extraction",
  12: "Data quality",
  13: "Data cleaning",
  14: "Graph construction",
  15: "Graph validation",
};
function BuildPage() {
  const { stage: stageParam } = useParams();
  const stage = Number(stageParam ?? 10);
  const { id, done, can } = useWorkspace();
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
  const [eventOffset, setEventOffset] = useState(0);
  const status = useQuery({
    queryKey: ["workspace", id, "build", "status"],
    queryFn: ({ signal }) => buildsApi.status(id, signal),
    refetchInterval: (q) =>
      q.state.data && ["queued", "running"].includes(q.state.data.status)
        ? 1500
        : false,
    retry: false,
  });
  const client = useQueryClient();
  const jobStatus = status.data?.status;
  useEffect(() => {
    if (jobStatus && ["completed", "blocked", "failed"].includes(jobStatus))
      void client.invalidateQueries({ queryKey: ["workspace", id, "session"] });
  }, [jobStatus, id, client]);
  const busy =
    status.data?.status === "running" || status.data?.status === "queued";
  const config = {
    batch_size: batch,
    business_rules: Object.keys(rules ?? {}).length ? rules : undefined,
  };
  const start = useAction((sid) => buildsApi.start(sid, config));
  const run = useAction((sid) => buildsApi.run(sid, stage, config));
  const result = useData(
    ["build", "result", stage, status.data?.status],
    (signal) => buildsApi.result(id, stage, signal),
    !busy &&
      (done.includes(stage) ||
        (stage === 12 && done.includes(11)) ||
        (stage === 15 && done.includes(14))),
  );
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
  const events = useQuery({
    queryKey: ["workspace", id, "build", "events", eventOffset],
    queryFn: ({ signal }) => sessionsApi.events(id, eventOffset, signal),
    refetchInterval: busy ? 2000 : false,
    retry: false,
  });
  if (!titles[stage])
    return (
      <Alert severity="error">Choose a build stage from 10 through 15.</Alert>
    );
  return (
    <>
      <PageHeader
        eyebrow={`${stage} / GRAPH CONSTRUCTION`}
        title={titles[stage]}
        description="Execute a single stage or run the complete build from planning through validation. Snapshot storage is a separate operation."
        action={
          <Button
            variant="contained"
            disabled={
              !can(stage) ||
              busy ||
              run.isPending ||
              !Number.isInteger(batch) ||
              batch < 1 ||
              batch > 100000
            }
            onClick={() => run.mutate()}
          >
            Run stage {stage}
          </Button>
        }
      />
      <Feedback
        pending={run.isPending || start.isPending}
        error={run.error || start.error}
      />
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_1.5fr] gap-5">
        <div className="flex flex-col gap-5">
          <Panel title="Build configuration">
            <div className="form-stack">
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
              <Button
                variant="contained"
                disabled={
                  !can(10) ||
                  busy ||
                  !Number.isInteger(batch) ||
                  batch < 1 ||
                  batch > 100000
                }
                onClick={() => setConfirm(true)}
              >
                Run full build · stages 10–15
              </Button>
            </div>
          </Panel>
          <Panel title="Stage navigation">
            <div className="flex flex-wrap gap-2">
              {Object.entries(titles).map(([n, t]) => (
                <Button
                  key={n}
                  component={Link}
                  to={`/build/${n}`}
                  variant={stage === Number(n) ? "contained" : "outlined"}
                  size="small"
                >
                  {n} · {t}
                </Button>
              ))}
            </div>
          </Panel>
        </div>
        <div className="flex flex-col gap-5">
          <Panel
            title="Build execution"
            action={
              <StatusChip done={status.data?.status === "completed"}>
                {status.data?.status ?? "Not started"}
              </StatusChip>
            }
          >
            <Feedback error={status.error} />
            {busy && <LinearProgress className="mb-4" />}
            <Report value={status.data} />
            {status.data?.status === "blocked" && (
              <Alert severity="warning">
                The build stopped at a blocking validation stage. Review its
                report before continuing.
              </Alert>
            )}
            {status.data?.status === "completed" && (
              <Button component={Link} to="/storage">
                Continue to snapshot storage
              </Button>
            )}
          </Panel>
          <Panel title="Stage results">
            <Feedback
              pending={result.isFetching}
              error={done.includes(stage) ? result.error : undefined}
            />
            <Report value={result.data} />
          </Panel>
        </div>
      </div>
      {stage === 11 && done.includes(11) && (
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
      {stage === 13 && done.includes(13) && (
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
      <div className="section-gap">
        <Panel title="Execution events">
          <Feedback error={events.error} />
          <DataTable rows={events.data?.items ?? []} />
          <div className="toolbar mt-3">
            <Button
              disabled={eventOffset === 0}
              onClick={() => setEventOffset(Math.max(0, eventOffset - 100))}
            >
              Previous
            </Button>
            <span className="muted">
              {eventOffset}–{eventOffset + (events.data?.items.length ?? 0)} of{" "}
              {events.data?.total ?? 0}
            </span>
            <Button
              disabled={eventOffset + 100 >= (events.data?.total ?? 0)}
              onClick={() => setEventOffset(eventOffset + 100)}
            >
              Next
            </Button>
          </div>
        </Panel>
      </div>
      <Confirm
        open={confirm}
        title="Start the complete graph build?"
        onClose={() => setConfirm(false)}
        onConfirm={() =>
          start.mutate(undefined, { onSuccess: () => setConfirm(false) })
        }
        pending={start.isPending}
      >
        <p>
          This executes stages 10–15 with the current approved ontology and
          configured rules. Saving a snapshot remains a separate action.
        </p>
        <Feedback error={start.error} />
      </Confirm>
    </>
  );
}

export default function BuildRoute() {
  const { stage } = useParams();
  return <BuildPage key={stage ?? "all"} />;
}
