import { Button, TextField } from "@mui/material";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { scopeApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import { Feedback, PageHeader, Panel } from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
const schema = z.object({
  project: z.string().trim().min(1, "Enter a project name.").max(200),
  business_questions: z
    .string()
    .trim()
    .min(1, "Add at least one business question."),
  tables_in_scope: z.string(),
  sensitive_columns: z.string(),
  users: z.string(),
  later_list: z.string(),
});
const lines = (s: string) =>
  s
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
function ScopeForm({
  scope,
}: {
  scope: Schema<"ScopeRequest"> | null | undefined;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    getValues,
    reset,
  } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      project: scope?.project ?? "",
      business_questions: scope?.business_questions.join("\n") ?? "",
      tables_in_scope: scope?.tables_in_scope?.join("\n") ?? "",
      sensitive_columns: scope?.sensitive_columns?.join("\n") ?? "",
      users: scope?.users?.join("\n") ?? "",
      later_list: scope?.later_list?.join("\n") ?? "",
    },
  });
  const save = useAction((id) => {
    const v = getValues();
    return scopeApi.save(id, {
      project: v.project,
      business_questions: lines(v.business_questions),
      tables_in_scope: lines(v.tables_in_scope),
      sensitive_columns: lines(v.sensitive_columns),
      users: lines(v.users),
      later_list: lines(v.later_list),
    });
  });
  return (
    <form onSubmit={handleSubmit(() => save.mutate(undefined,{onSuccess:()=>reset(getValues())}))} className="form-stack">
      <TextField
        label="Project name"
        {...register("project")}
        error={!!errors.project}
        helperText={errors.project?.message}
        required
      />
      <TextField
        label="Business questions — one per line"
        {...register("business_questions")}
        multiline
        minRows={3}
        error={!!errors.business_questions}
        helperText={errors.business_questions?.message}
        required
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <TextField
          label="Tables in scope — one per line"
          {...register("tables_in_scope")}
          multiline
          minRows={3}
          helperText="Qualified names, e.g. public.customers. Leave empty to include all tables."
        />
        <TextField
          label="Sensitive columns — one per line"
          {...register("sensitive_columns")}
          multiline
          minRows={3}
          helperText="Qualified names, e.g. public.customers.email"
        />
        <TextField
          label="Intended users — one per line"
          {...register("users")}
          multiline
          minRows={2}
        />
        <TextField
          label="Deferred scope — one per line"
          {...register("later_list")}
          multiline
          minRows={2}
        />
      </div>
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
        eyebrow="01 / DATA & METADATA"
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
