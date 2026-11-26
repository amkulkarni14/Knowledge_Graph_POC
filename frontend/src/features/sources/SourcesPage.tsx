import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Autocomplete,
  Button,
  MenuItem,
  TextField,
} from "@mui/material";
import { Cloud, Database, FlaskConical, Upload } from "lucide-react";
import { sourcesApi } from "../../api/workflowApi";
import { useSessionStore } from "../../app/store";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import {
  Confirm,
  Feedback,
  PageHeader,
  Panel,
  Report,
} from "../../shared/ui/WorkspaceUi";
import {
  guidedSources,
  labels,
  type ConnectorId,
  type ConnectionRequest,
} from "./guidedSources";
import {
  clearSecrets,
  ConnectionFields,
  defaultFields,
  UploadFields,
} from "./ConnectionFields";
import { SourceAssets } from "./SourceAssets";

const options = [
  {
    id: "sample",
    title: labels.sample,
    group: "Sample Data",
    icon: FlaskConical,
  },
  { id: "csv", title: labels.csv, group: "Local File Sources", icon: Upload },
  {
    id: "postgres",
    title: labels.postgres,
    group: "Relational Databases",
    icon: Database,
  },
  {
    id: "mssql",
    title: labels.mssql,
    group: "Relational Databases",
    icon: Database,
  },
  {
    id: "oracle",
    title: labels.oracle,
    group: "Relational Databases",
    icon: Database,
  },
  {
    id: "aws",
    title: "Amazon Web Services",
    group: "Cloud Data Sources",
    icon: Cloud,
  },
  {
    id: "azure",
    title: "Microsoft Azure",
    group: "Cloud Data Sources",
    icon: Cloud,
  },
  {
    id: "gcp",
    title: "Google Cloud Platform",
    group: "Cloud Data Sources",
    icon: Cloud,
  },
] as const;
const services = {
  aws: [
    ["s3", labels.s3],
    ["postgres", "Amazon RDS PostgreSQL"],
    ["mssql", "Amazon RDS SQL Server"],
    ["oracle", "Amazon RDS Oracle"],
  ],
  azure: [
    ["azure_blob", labels.azure_blob],
    ["azure_adls", labels.azure_adls],
    ["mssql", "Azure SQL Database"],
    ["postgres", "Azure Database for PostgreSQL"],
  ],
  gcp: [
    ["gcs", labels.gcs],
    ["bigquery", labels.bigquery],
    ["postgres", "Cloud SQL for PostgreSQL"],
    ["mssql", "Cloud SQL for SQL Server"],
  ],
} as const;

type SourceFamily = (typeof options)[number]["id"];
type Selection = { family: SourceFamily; kind: ConnectorId };

function isCloudFamily(family: SourceFamily): family is keyof typeof services {
  return Object.hasOwn(services, family);
}

function savedSelection(value: unknown): Selection | undefined {
  if (typeof value !== "string" || !Object.hasOwn(labels, value)) return;
  const kind = value as ConnectorId;
  const family = options.find(({ id }) => id === kind)?.id
    ?? options.find(({ id }) => isCloudFamily(id) && services[id].some(([key]) => key === kind))?.id;
  if (family) return { family, kind };
}

export default function SourcesPage() {
  const epoch = useSessionStore((state) => state.epoch);
  return <SourceConnectionPage key={epoch} />;
}

function SourceConnectionPage() {
  const { id, can, done, session } = useWorkspace();
  const client = useQueryClient();
  const manifest = useQuery({
    queryKey: ["source-types"],
    queryFn: ({ signal }) => guidedSources.types(signal),
    staleTime: Infinity,
  });
  const active = useData(["sources"], (signal) => sourcesApi.read(id, signal));
  const pendingKey = ["source-candidate"];
  const pending = useData(pendingKey, (signal) =>
    guidedSources.candidate(id, signal),
  );
  const candidate = pending.data;
  const [selection, setSelection] = useState<Selection | null>();
  const [name, setName] = useState("");
  const [configOverride, setConfig] = useState<Record<string, string>>();
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const [tested, setTested] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const restored = savedSelection(active.data?.mode)
    ?? savedSelection(session.data?.summary?.source_type);
  const pendingSelection = savedSelection(candidate?.source);
  const current = pendingSelection && selection?.kind !== pendingSelection.kind
    ? pendingSelection
    : selection === undefined ? restored : selection;
  const family = options.find(({ id }) => id === current?.family) ?? null;
  const kind = current?.kind;
  const group = family && isCloudFamily(family.id) ? services[family.id] : undefined;
  const spec = kind ? manifest.data?.[kind] : undefined;
  const config = configOverride ?? (kind ? defaultFields(kind, spec) : {});
  const method = config.authentication ?? "";
  const authFields = spec?.authentication[method] ?? [];
  const requiredFields = [...(spec?.required ?? []), ...authFields];
  const location = spec?.location;
  const cloud = !!location;
  const validFiles =
    files.length > 0 && files.every((file) => /\.csv$/i.test(file.name));
  const valid =
    !!spec &&
    (kind === "sample" ||
      (kind === "csv"
        ? validFiles
        : name.trim() &&
          requiredFields.every((field) => config[field]?.trim())));
  function request(): ConnectionRequest {
    if (!kind) throw new Error("Select a data source first.");
    const fields = new Set([...requiredFields, ...(spec?.optional ?? [])]);
    return {
      source: kind,
      name: name.trim() || labels[kind],
      configuration: {
        ...Object.fromEntries(
          Object.entries(config).filter(
            ([key, value]) => fields.has(key) && value !== "",
          ),
        ),
        ...(method && kind !== "postgres" ? { authentication: method } : {}),
      },
    };
  }
  const test = useAction((session) => guidedSources.test(session, request()), {
    invalidate: false,
  });
  const locate = useAction(
    (session) => guidedSources.locations(session, request()),
    { invalidate: false },
  );
  const connect = useAction(
    (session) =>
      kind === "csv"
        ? guidedSources.upload(session, files, setProgress)
        : guidedSources.connect(session, request()),
    { invalidate: false },
  );
  const disconnect = useAction(guidedSources.disconnect);
  const busy =
    test.isPending ||
    locate.isPending ||
    connect.isPending ||
    disconnect.isPending;
  const configured = done.includes(2);
  const refreshCandidate = () =>
    void client.invalidateQueries({
      queryKey: ["workspace", id, ...pendingKey],
    });
  function resetFeedback() {
    setTested(false);
    test.reset();
    locate.reset();
    connect.reset();
  }
  function choose(next: Selection | null) {
    setSelection(next);
    setConfig(undefined);
    setName("");
    setFiles([]);
    setProgress(0);
    resetFeedback();
  }

  return (
    <>
      <PageHeader
        eyebrow="Data & Metadata"
        title="Data Sources"
        description="Connect a source, preview its data, and confirm the assets for this workspace."
      />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <Panel title="Source Connection">
          <Feedback
            pending={manifest.isPending || pending.isLoading}
            error={manifest.error ?? pending.error}
          />
          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault();
              if (!valid || busy || candidate || !can(2)) return;
              connect.mutate(undefined, {
                onSuccess: ({ result }) => {
                  client.setQueryData(["workspace", id, ...pendingKey], result);
                  setFiles([]);
                },
                onSettled: () => setConfig((currentConfig) => currentConfig && clearSecrets(currentConfig)),
              });
            }}
          >
            <Autocomplete
              options={options}
              groupBy={(option) => option.group}
              value={family}
              getOptionLabel={(option) =>
                option.id === family?.id && group && kind ? labels[kind] : option.title}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              disabled={busy || !!candidate || manifest.isPending}
              onChange={(_, option) => {
                choose(option ? {
                  family: option.id,
                  kind: isCloudFamily(option.id) ? services[option.id][0][0] : option.id,
                } : null);
              }}
              renderInput={(params) => (
                <TextField {...params} label="Select data source" />
              )}
              renderOption={(props, option) => {
                const { key, ...attributes } = props;
                return (
                  <li key={key} {...attributes}>
                    <option.icon size={16} aria-hidden="true" />
                    &nbsp;{option.title}
                  </li>
                );
              }}
            />
            {group && family && (
              <TextField
                select
                label="Cloud service"
                value={kind}
                disabled={busy || !!candidate}
                onChange={(event) => {
                  const service = group.find(([key]) => key === event.target.value);
                  if (service) choose({ family: family.id, kind: service[0] });
                }}
              >
                {group.map(([key, title]) => (
                  <MenuItem key={key} value={key}>
                    {title}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {kind === "sample" && (
              <p className="muted">
                Explore the built-in retail sample with customers, orders and
                products.
              </p>
            )}
            {kind === "csv" && (
              <UploadFields
                files={files}
                setFiles={setFiles}
                valid={validFiles}
                busy={busy || !!candidate}
                progress={connect.isPending ? progress : null}
              />
            )}
            {spec && kind !== "sample" && kind !== "csv" && (
              <fieldset
                className="form-stack min-w-0"
                disabled={busy || !!candidate}
              >
                <TextField
                  label="Connection name"
                  required
                  value={name}
                  onChange={(event) => {
                    setName(event.target.value);
                    resetFeedback();
                  }}
                />
                <ConnectionFields
                  spec={spec}
                  values={config}
                  onChange={(next) => {
                    setConfig(next);
                    resetFeedback();
                  }}
                />
                {cloud && (
                  <Button
                    disabled={
                      !requiredFields
                        .filter((field) => field !== location)
                        .every((field) => config[field]?.trim())
                    }
                    onClick={() => locate.mutate()}
                  >
                    List accessible locations
                  </Button>
                )}
                {!!locate.data?.result.length && location && (
                  <TextField
                    select
                    label="Discovered locations"
                    value=""
                    onChange={(event) => {
                      setConfig({ ...config, [location]: event.target.value });
                      resetFeedback();
                    }}
                  >
                    {locate.data.result.map((location) => (
                      <MenuItem value={location} key={location}>
                        {location}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              </fieldset>
            )}
            <div className="toolbar">
              {kind && kind !== "sample" && kind !== "csv" && (
                <Button
                  disabled={!valid || busy || !!candidate || !can(2)}
                  onClick={() =>
                    test.mutate(undefined, { onSuccess: () => setTested(true) })
                  }
                >
                  Test connection
                </Button>
              )}
              <Button
                variant="contained"
                type="submit"
                disabled={!valid || busy || !!candidate || !can(2)}
              >
                {kind === "sample"
                  ? "Connect retail sample"
                  : kind === "csv"
                    ? "Analyze and connect files"
                    : "Connect"}
              </Button>
            </div>
            {tested && (
              <Alert severity="success">Connection test succeeded.</Alert>
            )}
            <Feedback
              pending={busy}
              error={test.error ?? locate.error ?? connect.error}
            />
          </form>
        </Panel>
        <Panel title="Connection Details">
          <Feedback
            pending={active.isFetching}
            error={active.error ?? disconnect.error}
          />
          {candidate && (
            <Report
              value={{ ...candidate, status: "Awaiting asset selection" }}
            />
          )}
          {configured ? (
            <Report value={{ ...active.data, status: "Active" }} />
          ) : (
            !candidate && <p className="muted">No active source.</p>
          )}
          {configured && (
            <Button
              disabled={busy || !!candidate}
              onClick={() => setConfirmDisconnect(true)}
            >
              Disconnect
            </Button>
          )}
        </Panel>
      </div>
      {candidate && (
        <div className="section-gap">
          <SourceAssets
            key={candidate.id}
            candidate={candidate}
            active={configured}
            changed={refreshCandidate}
          />
        </div>
      )}
      <Confirm
        open={confirmDisconnect}
        title="Disconnect the active source?"
        pending={disconnect.isPending}
        onClose={() => setConfirmDisconnect(false)}
        onConfirm={() =>
          disconnect.mutate(undefined, {
            onSuccess: () => setConfirmDisconnect(false),
          })
        }
      >
        <p>This clears downstream results for the current source.</p>
        <Feedback error={disconnect.error} />
      </Confirm>
    </>
  );
}
