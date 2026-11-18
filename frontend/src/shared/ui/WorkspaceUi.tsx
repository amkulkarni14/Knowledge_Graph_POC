import { Component, type ReactNode } from "react";
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
} from "@mui/material";
import { Chip } from "@heroui/react";
import type { JsonObject } from "../../types/common.types";
export const stringify = (v: unknown) =>
  typeof v === "string" ? v : (JSON.stringify(v, null, 2) ?? "—");
export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow ?? "KNOWLEDGE WORKSPACE"}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}
export function StatusChip({
  done,
  children,
}: {
  done?: boolean;
  children: ReactNode;
}) {
  return (
    <Chip color={done ? "success" : "default"} size="sm" variant="soft">
      {children}
    </Chip>
  );
}
export function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Feedback({
  pending,
  error,
  onRetry,
}: {
  pending?: boolean;
  error?: unknown;
  onRetry?: () => void;
}) {
  return (
    <>
      {pending && (
        <div className="loading" role="status">
          <CircularProgress size={18} /> Working…
        </div>
      )}
      {!!error && (
        <Alert
          severity="error"
          action={
            onRetry ? <Button onClick={onRetry}>Retry</Button> : undefined
          }
        >
          {error instanceof Error ? error.message : "Request failed."}
        </Alert>
      )}
    </>
  );
}
export function Report({ value }: { value: unknown }) {
  if (value == null)
    return (
      <p className="muted">
        No results yet. Run the operation to inspect its output.
      </p>
    );
  if (Array.isArray(value))
    return (
      <DataTable
        rows={value.map((v) =>
          typeof v === "object" && v !== null
            ? (v as JsonObject)
            : { value: v },
        )}
      />
    );
  if (typeof value === "object") {
    const obj = value as JsonObject;
    const blocking=obj.ok===false||(Array.isArray(obj.findings)&&obj.findings.some(f=>typeof f==='object'&&f!==null&&'severity' in f&&f.severity==='block'));
    return (
      <div className="report">
        {blocking && (
          <Alert severity="error">
            Validation found blocking issues. Review the findings before
            proceeding.
          </Alert>
        )}
        {obj.ok === true && (
          <Alert severity="success">Validation passed.</Alert>
        )}
        {Object.entries(obj).map(([key, v]) => (
          <div className="report-row" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            {typeof v === "object" && v !== null ? (
              <details>
                <summary>
                  Inspect {Array.isArray(v) ? `${v.length} items` : "details"}
                </summary>
                <pre>{stringify(v)}</pre>
              </details>
            ) : (
              <strong>{stringify(v)}</strong>
            )}
          </div>
        ))}
      </div>
    );
  }
  return <p>{String(value)}</p>;
}
export function DataTable({
  rows,
  offset = 0,
  total,
  onPage,
}: {
  rows: JsonObject[];
  offset?: number;
  total?: number;
  onPage?: (offset: number) => void;
}) {
  const cols = Array.from(new Set(rows.flatMap(Object.keys)));
  return (
    <>
      {!rows.length ? (
        <p className="muted">No records available.</p>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                {cols.map((c) => (
                  <TableCell key={c}>{c.replaceAll("_", " ")}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((r, i) => (
                <TableRow key={i}>
                  {cols.map((c) => (
                    <TableCell key={c}>
                      {typeof r[c] === "object" && r[c] !== null ? (
                        <details>
                          <summary>Details</summary>
                          <pre>{stringify(r[c])}</pre>
                        </details>
                      ) : (
                        stringify(r[c])
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {onPage && (
        <TablePagination
          component="div"
          count={total ?? rows.length}
          page={Math.floor(offset / 25)}
          rowsPerPage={25}
          rowsPerPageOptions={[25]}
          onPageChange={(_, p) => onPage(p * 25)}
        />
      )}
    </>
  );
}
export function Confirm({
  open,
  title,
  children,
  onClose,
  onConfirm,
  pending = false,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  onConfirm: () => void;
  pending?: boolean;
}) {
  return (
    <Dialog
      open={open}
      onClose={pending ? undefined : onClose}
      fullWidth
      maxWidth="sm"
    >
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>{children}</DialogContent>
      <DialogActions>
        <Button disabled={pending} onClick={onClose}>
          Back
        </Button>
        <Button disabled={pending} variant="contained" onClick={onConfirm}>
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
}
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <Alert
        severity="error"
        action={<Button onClick={() => location.reload()}>Reload</Button>}
      >
        The workspace could not render. Reload to try again.
      </Alert>
    ) : (
      this.props.children
    );
  }
}
