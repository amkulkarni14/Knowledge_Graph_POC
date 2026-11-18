import { AttributeEditor } from "./AttributeEditor";
import { useState, useMemo } from "react";
import { Button, TextField, MenuItem, Tabs, Tab, Alert } from "@mui/material";
import { type Node } from "@xyflow/react";
import { OntologyCanvas } from "./OntologyCanvas";
import { ontologyApi, metadataApi } from "../../api/workflowApi";
import {
  useAction,
  useData,
  useWorkspace,
} from "../../shared/hooks/useWorkspace";
import {
  Feedback,
  PageHeader,
  Panel,
  Report,
  Confirm,
} from "../../shared/ui/WorkspaceUi";
import type { Schema } from "../../types/common.types";
const split = (v: string) =>
  v
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
export default function OntologyPage() {
  const { id, done, can } = useWorkspace();
  const [mode, setMode] = useState<Schema<"DraftRequest">["mode"]>("template");
  const [ontologyId, setOntologyId] = useState("retail");
  const [name, setName] = useState("Retail Knowledge Graph");
  const [author, setAuthor] = useState("data.modeller");
  const [tab, setTab] = useState(0);
  const [selected, setSelected] = useState("");
  const [className, setClassName] = useState("");
  const [table, setTable] = useState("");
  const [keys, setKeys] = useState("");
  const [rename, setRename] = useState("");
  const [attributes, setAttributes] = useState("[]");
  const [relName, setRelName] = useState("");
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [relKeys, setRelKeys] = useState("");
  const [cardinality, setCardinality] =
    useState<Schema<"ApiRelationship">["cardinality"]>("N:1");
  const [relKind, setRelKind] = useState<"foreign_key" | "join_table">(
    "foreign_key",
  );
  const [raw, setRaw] = useState("");
  const [parseError, setParseError] = useState("");
  const [remove, setRemove] = useState<"class" | "relationship" | null>(null);
  const [relKey, setRelKey] = useState("");
  const draft = useData(
    ["ontology", "draft"],
    (signal) => ontologyApi.draft(id, signal),
    can(5),
  );
  const catalog = useData(
    ["catalog"],
    (signal) => metadataApi.catalog(id, signal),
    done.includes(3),
  );
  const onto = draft.data;
  const create = useAction((sid) =>
    ontologyApi.create(sid, {
      mode,
      ontology_id: ontologyId,
      name,
      namespace: `com.example.${ontologyId}`,
      author,
    }),
  );
  const save = useAction((sid) => ontologyApi.save(sid));
  const revert = useAction((sid) => ontologyApi.revert(sid));
  const add = useAction((sid) =>
    ontologyApi.addClass(sid, {
      definition: {
        name: className,
        description: "",
        origin: "manual",
        mapping: { source_table: table, key_columns: split(keys) },
        attributes: [],
      },
    }),
  );
  const renameAction = useAction((sid) =>
    ontologyApi.rename(sid, selected, { name: rename }),
  );
  const attrAction = useAction((sid) =>
    ontologyApi.attributes(sid, selected, {
      attributes: JSON.parse(attributes) as Schema<"ApiAttribute">[],
    }),
  );
  const relAction = useAction((sid) =>
    ontologyApi.relationship(sid, {
      definition: {
        name: relName,
        source_class: source,
        target_class: target,
        cardinality,
        directed: true,
        required: false,
        allow_cycles: true,
        multi_edge: false,
        description: "",
        origin: "manual",
        mapping: {
          kind: relKind,
          table,
          source_key_columns: split(keys),
          target_key_columns: split(relKeys),
        },
      },
    }),
  );
  const replace = useAction((sid) =>
    ontologyApi.replace(sid, {
      ontology: JSON.parse(raw) as Schema<"ApiOntology">,
    }),
  );
  const del = useAction((sid) =>
    remove === "class"
      ? ontologyApi.removeClass(sid, selected)
      : ontologyApi.removeRelationship(sid, relKey),
  );
  const nodes: Node[] = useMemo(
    () =>
      onto?.classes?.map((c, i) => ({
        id: c.name,
        position: { x: (i % 3) * 235 + 25, y: Math.floor(i / 3) * 130 + 25 },
        data: {
          label: (
            <div>
              <strong>{c.name}</strong>
              <div className="text-[10px] text-slate-500 mt-1">
                {c.mapping?.source_table ?? "Unmapped"} ·{" "}
                {c.attributes?.length ?? 0} attributes
              </div>
            </div>
          ),
        },
        style: {
          borderColor: "#b5cae2",
          borderRadius: 7,
          width: 205,
          background: "#fff",
          fontSize: 12,
        },
      })) ?? [],
    [onto],
  );
  const edges = useMemo(
    () =>
      onto?.relationships?.map((r, i) => ({
        id: String(i),
        source: r.source_class,
        target: r.target_class,
        label: r.name,
      })) ?? [],
    [onto],
  );
  function selectClass(n: string) {
    setSelected(n);
    setRename(n);
    setAttributes(
      JSON.stringify(
        onto?.classes?.find((c) => c.name === n)?.attributes ?? [],
        null,
        2,
      ),
    );
  }
  function jsonAction(text: string, run: () => void) {
    try {
      JSON.parse(text);
      setParseError("");
      run();
    } catch {
      setParseError("Enter valid JSON before applying changes.");
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="05 / ONTOLOGY ENGINEERING"
        title="Ontology studio"
        description="Model classes, relationships, and source mappings. Editor changes invalidate downstream results; save your draft before review."
        action={
          <div className="toolbar">
            <Button
              disabled={!onto || revert.isPending}
              onClick={() => revert.mutate()}
            >
              Revert saved draft
            </Button>
            <Button
              variant="contained"
              disabled={!onto || save.isPending}
              onClick={() => save.mutate()}
            >
              Save draft
            </Button>
          </div>
        }
      />
      <Feedback
        pending={save.isPending || revert.isPending}
        error={save.error || revert.error}
      />
      {!onto ? (
        <Panel title="Initialize an ontology">
          <div className="form-stack">
            <TextField
              select
              label="Draft mode"
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
            >
              {[
                ["template", "Retail template"],
                ["schema", "Draft from schema"],
                ["new", "Empty ontology"],
              ].map(([v, l]) => (
                <MenuItem value={v} key={v}>
                  {l}
                </MenuItem>
              ))}
            </TextField>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <TextField
                label="Ontology ID"
                value={ontologyId}
                onChange={(e) => setOntologyId(e.target.value)}
              />
              <TextField
                label="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <TextField
                label="Author"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
              />
            </div>
            <Button
              variant="contained"
              disabled={!can(5) || create.isPending}
              onClick={() => create.mutate()}
            >
              Create draft
            </Button>
            <Feedback pending={create.isPending} error={create.error} />
            {!can(5) && (
              <Alert severity="info">
                Complete metadata extraction and analysis first.
              </Alert>
            )}
          </div>
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-5">
            <Panel
              title={onto.name}
              action={
                <span className="muted">
                  {onto.classes?.length ?? 0} classes ·{" "}
                  {onto.relationships?.length ?? 0} relationships
                </span>
              }
            >
              <div
                className="graph-frame"
                role="region"
                aria-label="Ontology diagram"
              >
                <OntologyCanvas
                  nodes={nodes}
                  edges={edges}
                  onSelect={selectClass}
                />
              </div>
              <p className="muted mt-3">
                Select a class to inspect it. Canvas positions are presentation
                preferences.
              </p>
            </Panel>
            <Panel title="Model editor">
              <Tabs
                value={tab}
                onChange={(_, v: number) => setTab(v)}
                variant="scrollable"
                className="mb-5"
              >
                <Tab label="Classes" />
                <Tab label="Relationships" />
                <Tab label="Advanced" />
              </Tabs>
              {tab === 0 && (
                <div className="form-stack">
                  <TextField
                    select
                    label="Inspect existing class"
                    value={selected}
                    onChange={(e) => selectClass(e.target.value)}
                  >
                    <MenuItem value="">Choose a class</MenuItem>
                    {onto.classes?.map((c) => (
                      <MenuItem key={c.name} value={c.name}>
                        {c.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  {selected && (
                    <>
                      <TextField
                        label="Class name"
                        value={rename}
                        onChange={(e) => setRename(e.target.value)}
                      />
                      <div className="toolbar">
                        <Button
                          disabled={renameAction.isPending || !rename}
                          onClick={() => renameAction.mutate()}
                        >
                          Rename
                        </Button>
                        <Button
                          color="error"
                          onClick={() => setRemove("class")}
                        >
                          Remove class
                        </Button>
                      </div>
                      <AttributeEditor
                        key={
                          selected +
                          JSON.stringify(
                            onto?.classes?.find((c) => c.name === selected)
                              ?.attributes,
                          )
                        }
                        className={selected}
                        initial={
                          (onto?.classes?.find((c) => c.name === selected)
                            ?.attributes ?? []) as Schema<"ApiAttribute">[]
                        }
                        columns={Object.keys(
                          catalog.data?.tables[
                            onto?.classes?.find((c) => c.name === selected)
                              ?.mapping?.source_table ?? ""
                          ]?.columns ?? {},
                        )}
                      />
                      <details>
                        <summary>Attribute JSON editor</summary>
                        <TextField
                          label="Attributes (JSON array)"
                          multiline
                          minRows={6}
                          value={attributes}
                          onChange={(e) => setAttributes(e.target.value)}
                          helperText="name, data_type, source_column, required, pii, normalize, description"
                        />
                        <Button
                          disabled={attrAction.isPending}
                          onClick={() =>
                            jsonAction(attributes, () => attrAction.mutate())
                          }
                        >
                          Apply attributes
                        </Button>
                      </details>
                      <Report
                        value={
                          onto.classes?.find((c) => c.name === selected)
                            ?.mapping
                        }
                      />
                    </>
                  )}
                  <h3>Add class</h3>
                  <TextField
                    label="PascalCase class name"
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                  />
                  <TextField
                    select
                    label="Source table"
                    value={table}
                    onChange={(e) => setTable(e.target.value)}
                  >
                    <MenuItem value="">Choose a table</MenuItem>
                    {Object.keys(catalog.data?.tables ?? {}).map((t) => (
                      <MenuItem value={t} key={t}>
                        {t}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="Key columns — comma separated"
                    value={keys}
                    onChange={(e) => setKeys(e.target.value)}
                  />
                  <Button
                    variant="outlined"
                    disabled={!className || !table || !keys || add.isPending}
                    onClick={() => add.mutate()}
                  >
                    Add class
                  </Button>
                  <Feedback
                    error={add.error || renameAction.error || attrAction.error}
                  />
                </div>
              )}
              {tab === 1 && (
                <div className="form-stack">
                  <TextField
                    label="UPPER_SNAKE relationship name"
                    value={relName}
                    onChange={(e) => setRelName(e.target.value)}
                  />
                  {[
                    ["Source class", source, setSource],
                    ["Target class", target, setTarget],
                  ].map(([label, value, setter]) => (
                    <TextField
                      key={String(label)}
                      select
                      label={String(label)}
                      value={value as string}
                      onChange={(e) =>
                        (setter as (v: string) => void)(e.target.value)
                      }
                    >
                      <MenuItem value="">Choose a class</MenuItem>
                      {onto.classes?.map((c) => (
                        <MenuItem value={c.name} key={c.name}>
                          {c.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  ))}
                  <TextField
                    select
                    label="Cardinality"
                    value={cardinality}
                    onChange={(e) =>
                      setCardinality(e.target.value as typeof cardinality)
                    }
                  >
                    {["1:1", "1:N", "N:1", "M:N"].map((v) => (
                      <MenuItem key={v} value={v}>
                        {v}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label="Mapping kind"
                    value={relKind}
                    onChange={(e) =>
                      setRelKind(e.target.value as typeof relKind)
                    }
                  >
                    <MenuItem value="foreign_key">Foreign key</MenuItem>
                    <MenuItem value="join_table">Join table</MenuItem>
                  </TextField>
                  <TextField
                    select
                    label="Mapping table"
                    value={table}
                    onChange={(e) => setTable(e.target.value)}
                  >
                    {Object.keys(catalog.data?.tables ?? {}).map((t) => (
                      <MenuItem value={t} key={t}>
                        {t}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="Source key columns — comma separated"
                    value={keys}
                    onChange={(e) => setKeys(e.target.value)}
                  />
                  <TextField
                    label="Target key columns — comma separated"
                    value={relKeys}
                    onChange={(e) => setRelKeys(e.target.value)}
                  />
                  <Button
                    disabled={
                      !relName ||
                      !source ||
                      !target ||
                      !table ||
                      !keys ||
                      !relKeys ||
                      relAction.isPending
                    }
                    variant="outlined"
                    onClick={() => relAction.mutate()}
                  >
                    Add relationship
                  </Button>
                  <TextField
                    select
                    label="Existing relationship"
                    value={relKey}
                    onChange={(e) => setRelKey(e.target.value)}
                  >
                    <MenuItem value="">Choose relationship</MenuItem>
                    {onto.relationships?.map((r) => {
                      const key = `${r.source_class}-[${r.name}]->${r.target_class}`;
                      return (
                        <MenuItem key={key} value={key}>
                          {key}
                        </MenuItem>
                      );
                    })}
                  </TextField>
                  <Button
                    color="error"
                    disabled={!relKey}
                    onClick={() => setRemove("relationship")}
                  >
                    Remove relationship
                  </Button>
                  <Feedback error={relAction.error} />
                </div>
              )}
              {tab === 2 && (
                <div className="form-stack">
                  <p className="muted">
                    Edit the complete ontology to configure descriptions,
                    normalization, PII, resolution columns, watermarks,
                    relationship properties, and mapping options.
                  </p>
                  <Button onClick={() => setRaw(JSON.stringify(onto, null, 2))}>
                    Load current ontology into editor
                  </Button>
                  <TextField
                    label="Complete ontology JSON"
                    multiline
                    minRows={15}
                    value={raw}
                    onChange={(e) => setRaw(e.target.value)}
                  />
                  <Button
                    disabled={!raw || replace.isPending}
                    onClick={() => jsonAction(raw, () => replace.mutate())}
                  >
                    Apply ontology
                  </Button>
                  <Feedback error={replace.error} />
                </div>
              )}
              {parseError && <Alert severity="error">{parseError}</Alert>}
            </Panel>
          </div>
          <div className="section-gap">
            <Panel title="Accessible model representation">
              <Report
                value={{
                  classes: onto.classes,
                  relationships: onto.relationships,
                }}
              />
            </Panel>
          </div>
        </>
      )}
      <Confirm
        open={!!remove}
        title={`Remove ${remove ?? "item"}?`}
        onClose={() => setRemove(null)}
        pending={del.isPending}
        onConfirm={() =>
          del.mutate(undefined, {
            onSuccess: () => {
              setRemove(null);
              setSelected("");
              setRelKey("");
            },
          })
        }
      >
        <p>This changes the draft and invalidates downstream results.</p>
        <Feedback error={del.error} />
      </Confirm>
    </>
  );
}
