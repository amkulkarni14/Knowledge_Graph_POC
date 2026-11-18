import { useState } from "react";
import {
  Button,
  TextField,
  MenuItem,
  Tabs,
  Tab,
  LinearProgress,
  Alert,
} from "@mui/material";
import { Database, Upload, FlaskConical } from "lucide-react";
import { useForm } from "react-hook-form";
import { sourcesApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import {
  Feedback,
  PageHeader,
  Panel,
  Report,
} from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
function PostgresForm({ enabled }: { enabled: boolean }) {
  const {
    register,
    handleSubmit,
    getValues,
    setValue,
    formState: { errors },
  } = useForm<Schema<"PostgresRequest">>({
    defaultValues: {
      host: "",
      port: 5432,
      dbname: "",
      user: "",
      password: "",
      sslmode: "prefer",
      schemas: ["public"],
    },
  });
  const [schemas, setSchemas] = useState("public");
  const connect = useAction(async (id) => {
    const value = {
      ...getValues(),
      schemas: schemas
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      return await sourcesApi.postgres(id, value);
    } finally {
      setValue("password", "");
      value.password = "";
    }
  });
  return (
    <form
      className="form-stack"
      onSubmit={handleSubmit(() => connect.mutate())}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(["host", "dbname", "user", "password"] as const).map((name) => (
          <TextField
            key={name}
            label={
              {
                host: "Host",
                dbname: "Database",
                user: "Read-only user",
                password: "Password",
              }[name]
            }
            {...register(name, { required: true })}
            type={name === "password" ? "password" : "text"}
            autoComplete={name === "password" ? "new-password" : "off"}
            error={!!errors[name]}
            required
          />
        ))}
        <TextField
          label="Port"
          type="number"
          {...register("port", {
            valueAsNumber: true,
            min: 1,
            max: 65535,
            required: true,
          })}
          error={!!errors.port}
        />
        <TextField
          label="SSL mode"
          select
          defaultValue="prefer"
          {...register("sslmode")}
        >
          {[
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
          ].map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
      </div>
      <TextField
        label="Schemas — comma separated"
        value={schemas}
        onChange={(e) => setSchemas(e.target.value)}
        required
      />
      <Button
        type="submit"
        variant="contained"
        disabled={!enabled || connect.isPending}
      >
        Connect to PostgreSQL
      </Button>
      <Feedback pending={connect.isPending} error={connect.error} />
    </form>
  );
}
export default function SourcesPage() {
  const { id, can } = useWorkspace();
  const [mode, setMode] = useState(0);
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const source = useData(["sources"], (signal) => sourcesApi.read(id, signal));
  const sample = useAction((sid) => sourcesApi.sample(sid));
  const upload = useAction(async (sid) => {
    try {
      return await sourcesApi.upload(sid, files, setProgress);
    } finally {
      setFiles([]);
    }
  });
  const valid = files.every((f) => /\.(csv|tsv|txt)$/i.test(f.name));
  return (
    <>
      <PageHeader
        eyebrow="02 / DATA & METADATA"
        title="Connect your data"
        description="Use the built-in retail sample, upload related files, or connect a read-only PostgreSQL source."
      />
      {!can(2) && (
        <Alert severity="info" className="mb-4">
          Save your project scope before connecting a source.
        </Alert>
      )}
      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_1fr] gap-5">
        <Panel title="Source connection">
          <Tabs
            value={mode}
            onChange={(_, v: number) => setMode(v)}
            variant="scrollable"
            className="mb-6"
          >
            <Tab
              label="Sample"
              icon={<FlaskConical size={16} />}
              iconPosition="start"
            />
            <Tab
              label="Upload files"
              icon={<Upload size={16} />}
              iconPosition="start"
            />
            <Tab
              label="PostgreSQL"
              icon={<Database size={16} />}
              iconPosition="start"
            />
          </Tabs>
          {mode === 0 && (
            <div className="form-stack">
              <h3>Retail demonstration dataset</h3>
              <p className="muted">
                A built-in dataset with customers, orders, products, and
                deliberate data-quality issues. Compatible with the retail
                ontology template and offline AI fixture.
              </p>
              <Button
                variant="contained"
                disabled={!can(2) || sample.isPending}
                onClick={() => sample.mutate()}
              >
                Connect retail sample
              </Button>
              <Feedback pending={sample.isPending} error={sample.error} />
            </div>
          )}
          {mode === 1 && (
            <div className="form-stack">
              <p className="muted">
                Each CSV, TSV, or text file becomes a table. The backend infers
                keys and relationships. Upload related files together.
              </p>
              <Button component="label" variant="outlined">
                Choose files
                <input
                  aria-label="Choose source files"
                  type="file"
                  accept=".csv,.tsv,.txt"
                  multiple
                  hidden
                  onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                />
              </Button>
              {files.map((f) => (
                <p key={f.name} className="muted">
                  {f.name} · {(f.size / 1024).toFixed(1)} KB
                </p>
              ))}
              {!valid && (
                <Alert severity="error">Select CSV, TSV, or text files.</Alert>
              )}
              <Button
                variant="contained"
                disabled={
                  !can(2) || !files.length || !valid || upload.isPending
                }
                onClick={() => upload.mutate()}
              >
                Analyze and connect files
              </Button>
              {upload.isPending && (
                <>
                  <LinearProgress variant="determinate" value={progress} />
                  <p className="muted">
                    Upload {progress}% — server processing follows upload.
                  </p>
                </>
              )}
              <Feedback error={upload.error} />
            </div>
          )}
          {mode === 2 && <PostgresForm enabled={can(2)} />}
        </Panel>
        <Panel title="Connected source">
          <Feedback pending={source.isFetching} error={source.error} />
          <Report value={source.data} />
        </Panel>
      </div>
    </>
  );
}
