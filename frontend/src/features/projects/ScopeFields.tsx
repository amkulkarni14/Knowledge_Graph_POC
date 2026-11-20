import { TextField } from "@mui/material";
import type { FieldErrors, UseFormRegister } from "react-hook-form";
import { z } from "zod";
import type { Schema } from "../../types/common.types";

export const scopeSchema = z.object({
  project: z.string().trim().min(1, "Enter a project name.").max(200),
  business_questions: z
    .string()
    .trim()
    .min(1, "Add at least one business question."),
  scope_notes: z.string().trim().max(4000),
  columns_in_scope: z.string(),
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

export type ScopeValues = z.infer<typeof scopeSchema>;

export function scopeValues(
  scope?: Schema<"ScopeRequest"> | null,
): ScopeValues {
  return {
    project: scope?.project ?? "",
    business_questions: scope?.business_questions.join("\n") ?? "",
    scope_notes: scope?.scope_notes ?? "",
    columns_in_scope: scope?.columns_in_scope?.join("\n") ?? "",
    tables_in_scope: scope?.tables_in_scope?.join("\n") ?? "",
    sensitive_columns: scope?.sensitive_columns?.join("\n") ?? "",
    users: scope?.users?.join("\n") ?? "",
    later_list: scope?.later_list?.join("\n") ?? "",
  };
}

export function scopePayload(value: ScopeValues): Schema<"ScopeRequest"> {
  return {
    project: value.project,
    business_questions: lines(value.business_questions),
    scope_notes: value.scope_notes,
    columns_in_scope: lines(value.columns_in_scope),
    tables_in_scope: lines(value.tables_in_scope),
    sensitive_columns: lines(value.sensitive_columns),
    users: lines(value.users),
    later_list: lines(value.later_list),
  };
}

export function ScopeFields({
  register,
  errors,
}: {
  register: UseFormRegister<ScopeValues>;
  errors: FieldErrors<ScopeValues>;
}) {
  return (
    <>
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
      <TextField
        label="Scope notes"
        {...register("scope_notes")}
        multiline
        minRows={2}
        error={!!errors.scope_notes}
        helperText={errors.scope_notes?.message}
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
          label="Columns in scope"
          {...register("columns_in_scope")}
          multiline
          minRows={3}
          helperText="One qualified column per line, e.g. public.customers.id. Recorded for planning."
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
    </>
  );
}
