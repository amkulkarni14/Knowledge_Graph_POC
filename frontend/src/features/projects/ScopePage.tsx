import { Button, MenuItem, TextField } from "@mui/material";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { useDomains } from "../../api/libraryApi";
import { usePageSave } from "../../app/layout/pageSave";
import {
  ScopeFields,
  scopeSchema,
  scopePayload,
  scopeValues,
  type ScopeValues,
} from "./ScopeFields";
import { scopeApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import { Feedback, PageHeader, Panel } from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
function ScopeForm({
  scope,
}: {
  scope: Schema<"ScopeRequest"> | null | undefined;
}) {
  const domains = useDomains();
  const [domainId, setDomainId] = useState("");
  const selectedDomain = domains.data?.find((domain) => domain.id === domainId);
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    getValues,
    reset,
  } = useForm<ScopeValues>({
    resolver: zodResolver(scopeSchema),
    defaultValues: scopeValues(scope),
  });
  const save = useAction((id) => scopeApi.save(id, scopePayload(getValues())));
  const { done } = useWorkspace();
  // Save & Next: validate, then save. An untouched scope that is already saved is left alone,
  // because saving refreshes downstream results.
  usePageSave(async () => {
    if (!isDirty && done.includes(1)) return true;
    let valid = false;
    await handleSubmit(() => {
      valid = true;
    })();
    if (!valid) return false;
    await save.mutateAsync();
    reset(getValues());
    return true;
  });
  return (
    <form
      onSubmit={handleSubmit(() =>
        save.mutate(undefined, { onSuccess: () => reset(getValues()) }),
      )}
      className="form-stack"
    >
      <div className="toolbar">
        <TextField
          select
          label="Saved domain"
          value={domainId}
          onChange={(event) => setDomainId(event.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        >
          <MenuItem value="">Select a domain</MenuItem>
          {domains.data?.map((domain) => (
            <MenuItem key={domain.id} value={domain.id}>
              {domain.name}
            </MenuItem>
          ))}
        </TextField>
        <Button
          disabled={!selectedDomain || save.isPending}
          onClick={() => {
            if (selectedDomain)
              reset(scopeValues(selectedDomain), { keepDefaultValues: true });
          }}
        >
          Use domain
        </Button>
        <Button component={Link} to="/domains">
          Manage domains
        </Button>
      </div>
      <Feedback pending={domains.isLoading} error={domains.error} />
      <ScopeFields register={register} errors={errors} />
      <div className="toolbar">
        <Button type="submit" variant="contained" disabled={save.isPending}>
          Save scope
        </Button>
        {isDirty && <span className="muted">Unsaved changes</span>}
      </div>
      <Feedback pending={save.isPending} error={save.error} />
      {save.isSuccess && (
        <p role="status" className="muted">
          Scope saved. Downstream results have been refreshed.
        </p>
      )}
    </form>
  );
}
export default function ScopePage() {
  const { id } = useWorkspace();
  const data = useData(["scope"], (signal) => scopeApi.read(id, signal));
  const [loaded, setLoaded] = useState<
    Schema<"ScopeRequest"> | null | undefined
  >(undefined);
  useEffect(() => {
    if (data.data !== undefined) setLoaded(data.data);
  }, [data.data]);
  return (
    <>
      <PageHeader
        eyebrow="Data & Metadata"
        title="Define your scope"
        description="Describe the questions your graph should answer and identify the data that belongs in this workspace."
      />
      <Panel title="Project scope">
        <Feedback pending={data.isLoading} error={data.error} />
        {loaded !== undefined && <ScopeForm key={id} scope={loaded} />}
      </Panel>
    </>
  );
}
