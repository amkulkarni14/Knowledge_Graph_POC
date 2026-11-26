import { useEffect, useId, useRef, useState, type Ref } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Checkbox,
  TextField,
  Typography,
  createFilterOptions,
} from "@mui/material";
import {
  questionKey,
  questionLength,
  questionLimit,
  suggestedQuestions,
  type BusinessQuestion,
} from "../../constants/businessQuestions";

const selectAllOption = {
  id: "select-all",
  text: "Select All",
  category: "",
  source: "predefined",
} as const;
const options = [selectAllOption, ...suggestedQuestions];
const filterOptions = createFilterOptions<(typeof suggestedQuestions)[number]>({
  stringify: ({ category, text }) => `${category} ${text}`,
});
const help =
  "Select predefined business questions or add your own questions to define what your knowledge graph should answer.";

export function BusinessQuestionsField({
  questions,
  onChange,
  onBlur,
  inputRef,
  error,
  disabled,
  onDraftChange,
}: {
  questions: BusinessQuestion[];
  onChange: (questions: BusinessQuestion[]) => void;
  onBlur: () => void;
  inputRef: Ref<HTMLInputElement>;
  error?: string;
  disabled: boolean;
  onDraftChange: (pending: boolean) => void;
}) {
  const heading = useId();
  const selectedHeading = useId();
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState<string>();
  const customCount = useRef(0);
  const [draftError, setDraftError] = useState("");
  const pendingDraft = editing !== undefined || Boolean(draft.trim());
  useEffect(() => {
    onDraftChange(pendingDraft);
  }, [onDraftChange, pendingDraft]);
  const selectedKeys = new Set(questions.map(({ text }) => questionKey(text)));
  const predefinedTexts = new Set(
    questions
      .filter(({ source }) => source === "predefined")
      .map(({ text }) => text),
  );
  const predefined = suggestedQuestions.filter(({ text }) =>
    predefinedTexts.has(text),
  );
  const unselected = suggestedQuestions.filter(({ text }) =>
    !selectedKeys.has(questionKey(text)),
  );
  // A custom question with equivalent text already covers that catalog entry.
  const allSelected = predefined.length > 0 && unselected.length === 0;
  const partiallySelected = predefined.length > 0 && !allSelected;
  const exceedsLimit = questions.length + unselected.length > questionLimit;

  function clearPredefined() {
    onChange(questions.filter(({ source }) => source === "custom"));
  }

  function cancelEdit() {
    setEditing(undefined);
    setDraft("");
    setDraftError("");
  }

  function addOrUpdate() {
    const text = draft.trim().replace(/\s+/g, " ");
    if (!text) return setDraftError("Enter a business question.");
    if (Array.from(text).length > questionLength)
      return setDraftError(`Use ${questionLength} characters or fewer.`);
    if (
      questions.some(
        (question) =>
          question.id !== editing &&
          questionKey(question.text) === questionKey(text),
      )
    )
      return setDraftError("This business question is already selected.");
    if (editing === undefined && questions.length >= questionLimit)
      return setDraftError(`Select up to ${questionLimit} business questions.`);
    onChange(
      editing === undefined
        ? [
            ...questions,
            {
              id: `custom:${heading}:${++customCount.current}`,
              text,
              source: "custom",
            },
          ]
        : questions.map((question) =>
            question.id === editing ? { ...question, text } : question,
          ),
    );
    cancelEdit();
  }

  function remove(id: string) {
    onChange(questions.filter((question) => question.id !== id));
    if (editing === id) cancelEdit();
  }

  return (
    <section aria-labelledby={heading} className="form-stack min-w-0">
      <div>
        <Typography id={heading} component="h3" className="font-semibold">
          Business Questions<span aria-hidden="true">*</span>
        </Typography>
        <p className="muted">{help}</p>
      </div>
      <Autocomplete
        multiple
        disableCloseOnSelect
        disabled={disabled}
        options={options}
        value={allSelected ? [selectAllOption, ...predefined] : predefined}
        getOptionKey={(option) => option.id}
        getOptionLabel={(option) => option.text}
        getOptionDisabled={({ id, text }) =>
          id === selectAllOption.id
            ? !allSelected && (!unselected.length || exceedsLimit)
            : !predefinedTexts.has(text) &&
          (selectedKeys.has(questionKey(text)) ||
            questions.length >= questionLimit)
        }
        groupBy={(option) => option.category}
        filterOptions={(_, state) => [
          selectAllOption,
          ...filterOptions(suggestedQuestions, {
            ...state,
            inputValue: state.inputValue.replace(
              /\brelationships\b/gi,
              "relationship",
            ),
          }),
        ]}
        clearText="Clear predefined questions"
        renderValue={() => null}
        slotProps={{ listbox: { sx: {
          maxHeight: 300,
          "& > li:first-of-type": {
            position: "sticky",
            top: 0,
            zIndex: 2,
            bgcolor: "background.paper",
            "& > .MuiAutocomplete-groupLabel": { display: "none" },
          },
        } } }}
        onChange={(_, _values, reason, details) => {
          if (details?.option.id === selectAllOption.id) {
            if (allSelected) clearPredefined();
            else if (!exceedsLimit) onChange([...questions, ...unselected]);
            return;
          }
          if (reason === "selectOption" && details) {
            const { text } = details.option;
            if (
              !selectedKeys.has(questionKey(text)) &&
              questions.length < questionLimit
            )
              onChange([...questions, details.option]);
          } else if (reason === "removeOption" && details) {
            const question = questions.find(
              ({ source, text }) =>
                source === "predefined" && text === details.option.text,
            );
            if (question) remove(question.id);
          } else if (reason === "clear") {
            clearPredefined();
          }
        }}
        renderOption={(props, question, state) => {
          const { key, ...attributes } = props;
          const bulk = question.id === selectAllOption.id;
          return (
            <li key={key} {...attributes} aria-label={bulk ? selectAllOption.text : undefined}>
              <Checkbox
                checked={state.selected}
                indeterminate={bulk && partiallySelected}
                disabled={bulk && !allSelected && (exceedsLimit || !unselected.length)}
                tabIndex={-1}
                disableRipple
                aria-hidden={bulk ? undefined : true}
                slotProps={bulk ? { input: {
                  "aria-label": "Select All",
                  "aria-checked": partiallySelected ? "mixed" : allSelected,
                } } : undefined}
              />
              {question.text}
            </li>
          );
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Search and select business questions"
            placeholder="Search and select business questions"
            inputRef={inputRef}
            onBlur={onBlur}
            error={Boolean(error)}
            helperText={error}
          />
        )}
      />
      {exceedsLimit && !allSelected && <p className="muted">
        Select All would exceed the {questionLimit}-question limit.
      </p>}
      <div className="flex flex-wrap items-start gap-2">
        <TextField
          className="min-w-0 flex-[1_1_16rem]"
          label={
            editing === undefined
              ? "Add custom business question"
              : "Edit custom business question"
          }
          placeholder="e.g. Which entities are most affected when a critical dependency fails?"
          value={draft}
          disabled={disabled}
          error={Boolean(draftError)}
          helperText={draftError}
          onChange={(event) => {
            setDraft(event.target.value);
            setDraftError("");
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.nativeEvent.isComposing) {
              event.preventDefault();
              addOrUpdate();
            }
          }}
        />
        <Button
          type="button"
          variant="outlined"
          disabled={disabled}
          onClick={addOrUpdate}
        >
          {editing === undefined ? "Add question" : "Update question"}
        </Button>
        {editing !== undefined && (
          <Button type="button" onClick={cancelEdit} disabled={disabled}>
            Cancel edit
          </Button>
        )}
      </div>
      <section aria-labelledby={selectedHeading}>
        <Typography
          id={selectedHeading}
          component="h4"
          className="font-semibold"
        >
          Selected Business Questions
        </Typography>
        <p className="muted" aria-live="polite">
          Selected questions: {questions.length}
        </p>
        {questions.length ? (
          <ol className="list-decimal space-y-2 pl-5 mt-2">
            {questions.map((question, index) => (
              <li key={question.id}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <Box
                    sx={{
                      flex: "1 1 15rem",
                      minWidth: 0,
                      overflowWrap: "anywhere",
                    }}
                  >
                    <div>{question.text}</div>
                    <span className="muted">
                      {question.source === "predefined"
                        ? "Predefined"
                        : "Custom"}
                    </span>
                  </Box>
                  <div className="flex flex-wrap gap-1">
                    {question.source === "custom" && (
                      <Button
                        type="button"
                        size="small"
                        aria-label={`Edit question ${index + 1}`}
                        disabled={disabled}
                        onClick={() => {
                          setEditing(question.id);
                          setDraft(question.text);
                          setDraftError("");
                        }}
                      >
                        Edit
                      </Button>
                    )}
                    <Button
                      type="button"
                      size="small"
                      aria-label={`Remove question ${index + 1}`}
                      disabled={disabled}
                      onClick={() => remove(question.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted mt-2">
            No business questions selected. Choose from the suggestions or add
            your own.
          </p>
        )}
      </section>
    </section>
  );
}
