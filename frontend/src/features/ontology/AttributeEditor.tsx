import { useState } from "react";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  TextField,
} from "@mui/material";
import { ontologyApi } from "../../api/workflowApi";
import { useAction } from "../../shared/hooks/useWorkspace";
import { Feedback } from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
type Attribute = Schema<"ApiAttribute">;
export function AttributeEditor({
  className,
  initial,
  columns,
}: {
  className: string;
  initial: Attribute[];
  columns: string[];
}) {
  const [items, setItems] = useState<Attribute[]>(initial);
  const [name, setName] = useState("");
  const [column, setColumn] = useState("");
  const [type, setType] = useState<Attribute["data_type"]>("string");
  const [required, setRequired] = useState(false);
  const [pii, setPii] = useState(false);
  const [normalize, setNormalize] = useState("");
  const [description, setDescription] = useState("");
  const action = useAction((id) =>
    ontologyApi.attributes(id, className, { attributes: items }),
  );
  function edit(index: number, patch: Partial<Attribute>) {
    setItems((v) =>
      v.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  }
  return (
    <div className="form-stack">
      <h3>Attribute definitions</h3>
      {items.map((a, i) => (
        <div className="panel" key={i}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <TextField
              label={`Attribute ${i + 1} name`}
              value={a.name}
              onChange={(e) => edit(i, { name: e.target.value })}
            />
            <TextField
              label={`Attribute ${i + 1} source column`}
              select
              value={a.source_column ?? ""}
              onChange={(e) =>
                edit(i, { source_column: e.target.value || null })
              }
            >
              <MenuItem value="">Unmapped</MenuItem>
              {columns.map((c) => (
                <MenuItem value={c} key={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label={`Attribute ${i + 1} type`}
              select
              value={a.data_type}
              onChange={(e) =>
                edit(i, { data_type: e.target.value as Attribute["data_type"] })
              }
            >
              {[
                "string",
                "integer",
                "float",
                "decimal",
                "boolean",
                "date",
                "datetime",
                "json",
              ].map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label={`Attribute ${i + 1} normalization`}
              select
              value={a.normalize ?? ""}
              onChange={(e) =>
                edit(i, {
                  normalize: (e.target.value || null) as Attribute["normalize"],
                })
              }
            >
              {["", "trim", "lower", "upper", "title"].map((t) => (
                <MenuItem key={t} value={t}>
                  {t || "None"}
                </MenuItem>
              ))}
            </TextField>
          </div>
          <div className="toolbar">
            <FormControlLabel
              control={
                <Checkbox
                  checked={a.required ?? false}
                  onChange={(e) => edit(i, { required: e.target.checked })}
                />
              }
              label="Required"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={a.pii ?? false}
                  onChange={(e) => edit(i, { pii: e.target.checked })}
                />
              }
              label="PII"
            />
            <Button
              color="error"
              onClick={() => setItems((v) => v.filter((_, n) => n !== i))}
            >
              Remove attribute {a.name}
            </Button>
          </div>
        </div>
      ))}
      <h3>Add an attribute</h3>
      <TextField
        label="New attribute name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        helperText="snake_case"
      />
      <TextField
        label="New attribute source column"
        select
        value={column}
        onChange={(e) => setColumn(e.target.value)}
      >
        <MenuItem value="">Unmapped</MenuItem>
        {columns.map((c) => (
          <MenuItem key={c} value={c}>
            {c}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        label="New attribute data type"
        select
        value={type}
        onChange={(e) => setType(e.target.value as Attribute["data_type"])}
      >
        {[
          "string",
          "integer",
          "float",
          "decimal",
          "boolean",
          "date",
          "datetime",
          "json",
        ].map((t) => (
          <MenuItem key={t} value={t}>
            {t}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        label="New attribute normalization"
        select
        value={normalize}
        onChange={(e) => setNormalize(e.target.value)}
      >
        {["", "trim", "lower", "upper", "title"].map((t) => (
          <MenuItem key={t} value={t}>
            {t || "None"}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        label="New attribute description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="toolbar">
        <FormControlLabel
          control={
            <Checkbox
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
            />
          }
          label="Required"
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={pii}
              onChange={(e) => setPii(e.target.checked)}
            />
          }
          label="PII"
        />
      </div>
      <Button
        disabled={
          !/^[a-z][a-z0-9_]{0,62}$/.test(name) ||
          items.some((i) => i.name === name)
        }
        onClick={() => {
          setItems((v) => [
            ...v,
            {
              name,
              data_type: type,
              required,
              pii,
              normalize: (normalize || null) as Attribute["normalize"],
              source_column: column || null,
              description,
              origin: "manual",
            },
          ]);
          setName("");
        }}
      >
        Add attribute to list
      </Button>
      <Button
        variant="outlined"
        disabled={
          action.isPending ||
          items.some((a) => !/^[a-z][a-z0-9_]{0,62}$/.test(a.name))
        }
        onClick={() => action.mutate()}
      >
        Save attribute definitions
      </Button>
      <Feedback pending={action.isPending} error={action.error} />
    </div>
  );
}
