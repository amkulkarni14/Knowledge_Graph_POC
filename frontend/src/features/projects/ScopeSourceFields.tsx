import { Autocomplete, Checkbox, TextField, createFilterOptions } from "@mui/material";
import { sourcesApi } from "../../api/workflowApi";
import { useData, useWorkspace } from "../../shared/hooks/useWorkspace";
import { Feedback } from "../../shared/ui/WorkspaceUi";
import type { ScopeValues } from "./ScopeFields";

type SelectionFields = Pick<ScopeValues, "tables_in_scope" | "columns_in_scope" | "sensitive_columns">;
type Choice = { value: string; group: string };
const all = { value: "Select All", group: "" };
const clear = { value: "Clear All", group: "" };
const noMatches = { value: "No matching options", group: "" };
const filter = createFilterOptions<Choice>({ stringify: (option) => option.value });
const valuesOf = (value: string) => [...new Set(value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean))];
const tablePattern = /^[A-Za-z_][A-Za-z0-9_]{0,62}\.[A-Za-z_][A-Za-z0-9_]{0,62}$/;
const columnPattern = /^[A-Za-z_][A-Za-z0-9_]{0,62}\.[A-Za-z_][A-Za-z0-9_]{0,62}\.[A-Za-z_][A-Za-z0-9_]{0,62}$/;

function ScopePicker({ label, choices, value, onChange, helper, grouped, bulk, loading, disabled, limit }: {
  label: string;
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  helper?: string;
  grouped?: boolean;
  bulk?: boolean;
  loading: boolean;
  disabled: boolean;
  limit: number;
}) {
  const selected = new Set(value);
  const byValue = new Map(choices.map((choice) => [choice.value, choice]));
  const availableCount = choices.filter((choice) => selected.has(choice.value)).length;
  const allSelected = availableCount > 0 && availableCount === choices.length;
  const partial = availableCount > 0 && !allSelected;
  const canSelectAll = value.length + choices.length - availableCount <= limit;
  const actions = [...(bulk && choices.length ? [all] : []), ...(choices.length || value.length ? [clear] : [])];
  return <div>
    <Autocomplete
      multiple
      disableCloseOnSelect
      disableClearable
      disabled={disabled}
      loading={loading}
      options={[...actions, ...choices]}
      value={value.map((item) => byValue.get(item) ?? { value: item, group: "" })}
      groupBy={grouped ? (item) => item.group : undefined}
      getOptionLabel={(item) => item.value}
      isOptionEqualToValue={(item, selectedItem) => item.value === selectedItem.value}
      filterOptions={(_, state) => {
        const matches = filter(choices, state);
        return [...actions, ...(choices.length && !matches.length ? [noMatches] : matches)];
      }}
      noOptionsText={choices.length ? "No matching options" : "No source metadata available"}
      getOptionDisabled={(item) => {
        if (item === noMatches) return true;
        if (item === clear) return value.length === 0;
        if (item === all) return !allSelected && !canSelectAll;
        return !selected.has(item.value) && value.length >= limit;
      }}
      onChange={(_, items, _reason, details) => {
        if (details?.option === all) {
          if (allSelected) onChange([]);
          else if (canSelectAll) onChange([...new Set([...value, ...choices.map((item) => item.value)])]);
        } else if (details?.option === clear) onChange([]);
        else onChange([...new Set(items.map((item) => item.value))]);
      }}
      renderOption={(props, item, state) => {
        const { key, ...attributes } = props;
        return <li key={key} {...attributes} aria-selected={item === all ? allSelected : state.selected}>
          {item !== clear && item !== noMatches && <Checkbox checked={item === all ? allSelected : state.selected}
            indeterminate={item === all && partial} tabIndex={-1} disableRipple aria-hidden="true" />}
          {item.value}
        </li>;
      }}
      slotProps={{ listbox: { sx: grouped && actions.length ? {
        "& > li:first-of-type > .MuiAutocomplete-groupLabel": { display: "none" },
      } : undefined } }}
      renderInput={(params) => <TextField {...params} label={label}
        helperText={`${value.length} selected.${helper ? ` ${helper}` : ""}${
          bulk && !canSelectAll && !allSelected ? ` Select All exceeds the ${limit}-item limit.` : ""
        }`} />}
    />
  </div>;
}

export function ScopeSourceFields({ values, onChange, disabled }: {
  values: SelectionFields;
  onChange: (name: keyof SelectionFields, value: string) => void;
  disabled: boolean;
}) {
  const { id, done, session } = useWorkspace();
  const sourceReady = done.includes(2) && !session.data?.reconnect_required;
  const metadata = useData(["source-scope-schema", session.data?.source_version],
    (signal) => sourcesApi.schema(id, signal), sourceReady);
  const catalog = sourceReady ? metadata.data : undefined;
  const tables = valuesOf(values.tables_in_scope);
  const columns = valuesOf(values.columns_in_scope);
  const sensitive = valuesOf(values.sensitive_columns);
  const tableChoices = Object.keys(catalog ?? {}).filter((name) => tablePattern.test(name))
    .map((value) => ({ value, group: "" }));
  const columnsFor = (tableScope: string[]) => Object.entries(catalog ?? {})
    .filter(([table]) => !tableScope.length || tableScope.includes(table))
    .flatMap(([group, names]) => names.map((name) => ({ group, value: `${group}.${name}` })));
  const inScope = columnsFor(tables);
  function update(name: keyof SelectionFields, items: string[]) {
    onChange(name, items.join("\n"));
  }
  const picker = { loading: sourceReady && metadata.isLoading, disabled };
  return <>
    {(!sourceReady || metadata.isLoading || metadata.error) && <div className="md:col-span-2">
      {!sourceReady
        ? <p className="muted">Confirm or reconnect a data source to browse tables and columns.</p>
        : <Feedback pending={metadata.isLoading} error={metadata.error} onRetry={() => void metadata.refetch()} />}
    </div>}
    <ScopePicker {...picker} label="Tables in scope" helper="Leave empty to include all tables."
      value={tables} choices={tableChoices} limit={200} bulk onChange={(next) => {
        update("tables_in_scope", next);
        if (catalog) {
          const allowed = new Set(columnsFor(next).map((item) => item.value));
          if (columns.some((column) => !allowed.has(column)))
            update("columns_in_scope", columns.filter((column) => allowed.has(column)));
          if (sensitive.some((column) => !allowed.has(column)))
            update("sensitive_columns", sensitive.filter((column) => allowed.has(column)));
        }
      }} />
    <ScopePicker {...picker} label="Columns in scope" helper="Recorded for planning." value={columns} grouped bulk limit={1000}
      choices={inScope.filter(({ value }) => columnPattern.test(value))}
      onChange={(items) => update("columns_in_scope", items)} />
    <ScopePicker {...picker} label="Sensitive columns" value={sensitive} grouped limit={1000}
      choices={inScope.filter(({ value }) => value.length <= 200)}
      onChange={(items) => update("sensitive_columns", items)} />
  </>;
}
