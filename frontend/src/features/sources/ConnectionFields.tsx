import {
  Alert,
  Button,
  LinearProgress,
  MenuItem,
  TextField,
} from "@mui/material";
import type { ConnectorId, ConnectorSpec } from "./guidedSources";

const authenticationLabels: Record<string, string> = {
  password: "Username and password",
  default: "Default credentials",
  key: "Access key",
  temporary: "Temporary credentials",
  sas: "SAS token",
  principal: "Microsoft Entra service principal",
};
const names: Record<string, string> = {
  host: "Host",
  port: "Port",
  dbname: "Database",
  database: "Database",
  user: "Read-only user",
  password: "Password",
  sslmode: "SSL mode",
  schema: "Schema",
  schemas: "Schemas",
  identifier: "Service name or SID",
  identifier_type: "Connection identifier",
  region: "AWS region",
  bucket: "Bucket",
  prefix: "Path prefix",
  endpoint: "Custom S3 endpoint",
  account: "Storage account",
  container: "Container or filesystem",
  tenant: "Tenant ID",
  client: "Client ID",
  client_secret: "Client secret",
  account_key: "Account access key",
  sas: "SAS token",
  access_key: "Access key ID",
  secret_key: "Secret access key",
  session_token: "Session token",
  project: "Project ID",
  dataset: "Dataset",
  location: "Location",
};
const secret = new Set([
  "password",
  "client_secret",
  "account_key",
  "sas",
  "access_key",
  "secret_key",
  "session_token",
]);

export function clearSecrets(values: Record<string, string>) {
  return Object.fromEntries(
    Object.entries(values).filter(([key]) => !secret.has(key)),
  );
}

export function defaultFields(
  kind: ConnectorId,
  spec?: ConnectorSpec,
): Record<string, string> {
  const defaults: Partial<Record<ConnectorId, Record<string, string>>> = {
    postgres: { port: "5432", sslmode: "verify-full", schemas: "public" },
    mssql: { port: "1433", schema: "dbo" },
    oracle: { port: "1521", identifier_type: "service" },
    s3: { region: "us-east-1" },
  };
  return {
    ...defaults[kind],
    authentication: Object.keys(spec?.authentication ?? {})[0] ?? "",
  };
}

export function ConnectionFields({
  spec,
  values,
  onChange,
}: {
  spec: ConnectorSpec;
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
}) {
  function field(key: string, required: boolean) {
    const input = {
      label: names[key] ?? key,
      value: values[key] ?? "",
      required,
      onChange: (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
      ) => onChange({ ...values, [key]: event.target.value }),
    };
    if (key === "sslmode")
      return (
        <TextField key={key} {...input} select>
          <MenuItem value="verify-full">
            Verify certificate and hostname
          </MenuItem>
          <MenuItem value="disable">
            Disable for approved local development
          </MenuItem>
        </TextField>
      );
    if (key === "identifier_type")
      return (
        <TextField key={key} {...input} select>
          <MenuItem value="service">Service name</MenuItem>
          <MenuItem value="sid">SID</MenuItem>
        </TextField>
      );
    return (
      <TextField
        key={key}
        {...input}
        type={secret.has(key) ? "password" : key === "port" ? "number" : "text"}
        autoComplete={secret.has(key) ? "new-password" : undefined}
      />
    );
  }
  return (
    <>
      {spec.required.map((key) => field(key, true))}
      {Object.keys(spec.authentication).length > 0 && (
        <TextField
          select
          label="Authentication"
          value={values.authentication ?? ""}
          onChange={(event) =>
            onChange({
              ...clearSecrets(values),
              authentication: event.target.value,
            })
          }
        >
          {Object.keys(spec.authentication).map((method) => (
            <MenuItem key={method} value={method}>
              {authenticationLabels[method]}
            </MenuItem>
          ))}
        </TextField>
      )}
      {(spec.authentication[values.authentication] ?? []).map((key) =>
        field(key, true),
      )}
      {!!spec.optional?.length && (
        <details>
          <summary>Advanced settings</summary>
          <div className="form-stack mt-3">
            {spec.optional.map((key) => field(key, false))}
          </div>
        </details>
      )}
    </>
  );
}

export function UploadFields({
  files,
  setFiles,
  valid,
  busy,
  progress,
}: {
  files: File[];
  setFiles: (value: File[]) => void;
  valid: boolean;
  busy: boolean;
  progress: number | null;
}) {
  function add(incoming: File[]) {
    setFiles([
      ...new Map(
        [...files, ...incoming].map((file) => [file.name, file]),
      ).values(),
    ]);
  }
  return (
    <div
      className="form-stack"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        if (!busy) add(Array.from(event.dataTransfer.files));
      }}
    >
      <p className="muted">Drop CSV files here or choose files.</p>
      <Button component="label" variant="outlined" disabled={busy}>
        Choose files
        <input
          type="file"
          multiple
          hidden
          aria-label="Choose source files"
          accept=".csv"
          disabled={busy}
          onChange={(event) => {
            add(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
      </Button>
      {files.map((file) => (
        <div className="toolbar" key={file.name}>
          <span>
            {file.name} ({(file.size / 1024).toFixed(1)} KB)
          </span>
          <Button
            disabled={busy}
            onClick={() =>
              setFiles(files.filter((item) => item.name !== file.name))
            }
          >
            Remove {file.name}
          </Button>
        </div>
      ))}
      {!!files.length && !valid && (
        <Alert severity="error">Choose files in CSV format.</Alert>
      )}
      {progress !== null && (
        <LinearProgress
          aria-label="Upload progress"
          variant="determinate"
          value={progress}
        />
      )}
    </div>
  );
}
