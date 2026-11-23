import { useState } from "react";
import { Button, TextField } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { libraryApi, useDomains } from "../../api/libraryApi";
import { usePageSave } from "../../app/layout/pageSave";
import { Feedback, PageHeader, Panel } from "../../shared/ui/WorkspaceUi";
import {
  ScopeFields,
  scopePayload,
  scopeSchema,
  scopeValues,
  type ScopeValues,
} from "./ScopeFields";

export default function DomainsPage() {
  const client = useQueryClient();
  const domains = useDomains();
  const [name, setName] = useState("");
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ScopeValues>({
    resolver: zodResolver(scopeSchema),
    defaultValues: scopeValues(),
  });
  const save = useMutation({
    mutationFn: (values: ScopeValues) =>
      libraryApi.createDomain({ name: name.trim(), ...scopePayload(values) }),
    onSuccess: async () => {
      setName("");
      reset(scopeValues());
      await client.invalidateQueries({ queryKey: ["domains"] });
    },
  });
  // Save & Next: save the domain being typed, if any; otherwise just move on.
  usePageSave(async () => {
    if (!name.trim()) return true;
    let values = null as ScopeValues | null;
    await handleSubmit((valid) => {
      values = valid;
    })();
    if (!values) return false;
    await save.mutateAsync(values);
    return true;
  });
  return (
    <>
      <PageHeader
        title="Domains"
        description="Save reusable settings for Goal & Scope."
      />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <Panel title="Create a domain">
          <form
            className="form-stack"
            onSubmit={handleSubmit((values) => save.mutate(values))}
          >
            <TextField
              label="Domain name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              slotProps={{ htmlInput: { maxLength: 200 } }}
            />
            <ScopeFields register={register} errors={errors} />
            <Button
              type="submit"
              variant="contained"
              disabled={!name.trim() || save.isPending}
            >
              Save domain
            </Button>
            <Feedback pending={save.isPending} error={save.error} />
          </form>
        </Panel>
        <Panel title="Saved domains">
          <Feedback pending={domains.isLoading} error={domains.error} />
          {domains.data?.length === 0 && (
            <p className="muted">No domains saved yet.</p>
          )}
          {domains.data?.map((domain) => (
            <details key={domain.id} className="mb-3">
              <summary className="cursor-pointer font-semibold">
                {domain.name}
              </summary>
              <div className="report-row">
                <span>Project</span>
                <strong>{domain.project}</strong>
              </div>
              {domain.scope_notes && (
                <p className="whitespace-pre-wrap">{domain.scope_notes}</p>
              )}
              {(
                [
                  ["Business questions", domain.business_questions],
                  ["Tables in scope", domain.tables_in_scope],
                  ["Columns in scope", domain.columns_in_scope],
                  ["Sensitive columns", domain.sensitive_columns],
                  ["Intended users", domain.users],
                  ["Deferred scope", domain.later_list],
                ] as const
              ).map(([label, items]) =>
                items?.length ? (
                  <div key={label} className="my-2">
                    <strong>{label}</strong>
                    <ul className="list-disc pl-5">
                      {items.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null,
              )}
            </details>
          ))}
        </Panel>
      </div>
    </>
  );
}
