import { Button, MenuItem, TextField } from "@mui/material";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { z } from "zod";
import { useUiStore } from "../../app/store";
import {
  questionKey,
  questionLength,
  questionLimit,
  restoreBusinessQuestions,
} from "../../constants/businessQuestions";
import { BusinessQuestionsField } from "./BusinessQuestionsField";
import { ScopeSourceFields } from "./ScopeSourceFields";
import { useDomains } from "../../api/libraryApi";
import {
  ScopeFields,
  scopeSchema,
  scopePayload,
  scopeValues,
} from "./ScopeFields";
import { scopeApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import { Feedback, PageHeader, Panel } from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
const workspaceScopeSchema = scopeSchema.extend({
  business_questions: z
    .array(
      z.object({
        id: z.string(),
        text: z.string(),
        category: z.string().optional(),
        source: z.enum(["predefined", "custom"]),
      }),
    )
    .superRefine((questions, context) => {
      let message: string | undefined;
      const keys = questions.map(({ text }) => questionKey(text));
      if (!questions.length || keys.some((key) => !key))
        message =
          "Add at least one business question and remove any empty questions.";
      else if (questions.length > questionLimit)
        message = `Select up to ${questionLimit} business questions.`;
      else if (
        questions.some(({ text }) => Array.from(text).length > questionLength)
      )
        message = `Each business question must be ${questionLength} characters or fewer.`;
      else if (new Set(keys).size !== keys.length)
        message = "Remove duplicate business questions.";
      if (message) context.addIssue({ code: "custom", message });
    }),
});
type WorkspaceScopeValues = z.infer<typeof workspaceScopeSchema>;

function workspaceScopeValues(
  scope?: Schema<"ScopeRequest"> | null,
): WorkspaceScopeValues {
  return {
    ...scopeValues(scope),
    business_questions: restoreBusinessQuestions(
      scope?.business_questions ?? [],
    ),
  };
}

function ScopeForm({
  scope,
}: {
  scope: Schema<"ScopeRequest"> | null | undefined;
}) {
  const domains = useDomains();
  const { session } = useWorkspace();
  const [selectedDomainId, setDomainId] = useState<string>();
  const domainId = selectedDomainId ?? session.data?.domain_id ?? "";
  const [questionRevision, setQuestionRevision] = useState(0);
  const [questionDraft, setQuestionDraft] = useState(false);
  const selectedDomain = domains.data?.find((domain) => domain.id === domainId);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
    setValue,
  } = useForm<WorkspaceScopeValues>({
    resolver: zodResolver(workspaceScopeSchema),
    defaultValues: workspaceScopeValues(scope),
  });
  const [tables, columns, sensitive] = useWatch({
    control, name: ["tables_in_scope", "columns_in_scope", "sensitive_columns"],
  });
  const setScopeDirty = useUiStore((state) => state.setScopeDirty);
  const unsaved = isDirty || questionDraft;
  useLayoutEffect(() => {
    setScopeDirty(unsaved);
    return () => setScopeDirty(false);
  }, [unsaved, setScopeDirty]);
  const submitted = useRef<WorkspaceScopeValues | null>(null);
  const save = useAction((id) => {
    const values = submitted.current!;
    return scopeApi.save(
      id,
      { ...scopePayload({
        ...values,
        business_questions: values.business_questions.map(({ text }) => text),
      }), ...(domainId ? { domain_id: domainId } : {}) },
    );
  });
  return (
    <form
      onSubmit={handleSubmit((values) => {
        if (save.isPending || questionDraft) return;
        submitted.current = values;
        save.mutate(undefined, { onSuccess: () => reset(values) });
      })}
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
            if (selectedDomain) {
              reset(workspaceScopeValues(selectedDomain), {
                keepDefaultValues: true,
              });
              setQuestionRevision((value) => value + 1);
              setQuestionDraft(false);
            }
          }}
        >
          Use domain
        </Button>
        <Button component={Link} to="/domains">
          Manage domains
        </Button>
      </div>
      <Feedback pending={domains.isLoading} error={domains.error} />
      <fieldset className="form-stack min-w-0" disabled={save.isPending}>
        <ScopeFields
          register={register}
          errors={errors}
          sourceSelectors={<ScopeSourceFields
            values={{ tables_in_scope: tables, columns_in_scope: columns, sensitive_columns: sensitive }}
            onChange={(name, value) => setValue(name, value, { shouldDirty: true })}
            disabled={save.isPending}
          />}
          businessQuestions={
            <Controller
              name="business_questions"
              control={control}
              render={({ field, fieldState }) => (
                <BusinessQuestionsField
                  key={questionRevision}
                  questions={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  inputRef={field.ref}
                  error={fieldState.error?.message}
                  disabled={save.isPending}
                  onDraftChange={setQuestionDraft}
                />
              )}
            />
          }
        />
      </fieldset>
      <div className="toolbar">
        <Button
          type="submit"
          variant="contained"
          disabled={save.isPending || questionDraft}
        >
          Save scope
        </Button>
        {questionDraft ? (
          <span className="muted">
            Finish adding or editing the question before saving.
          </span>
        ) : (
          isDirty && <span className="muted">Unsaved changes</span>
        )}
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
  return <WorkspaceScope key={id} id={id} />;
}

function WorkspaceScope({ id }: { id: string }) {
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
