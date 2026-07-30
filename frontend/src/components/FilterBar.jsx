// Structured filter bar for list screens (#20, ADR #25).
//
// Renders one control per `filterField` and emits a params object mapped to the
// backend's query parameters. Supported filter kinds:
//   text                -> ?<name>=value (server does search/ilike where supported)
//   codeValue / ref     -> ?<name>=<id>  (exact match; dropdown via ComboField)
//   dateRange           -> ?<from>=..&<to>=..   (fromParam/toParam)
//   numberRange         -> ?<min>=..&<max>=..   (minParam/maxParam)
//
// The parent (EntityManager) merges the emitted params into DataTable extraParams.
import { useState } from "react";
import { Button, Label, Input, FlexBox } from "@ui5/webcomponents-react";
import ComboField from "./ComboField";

function buildParams(fields, state) {
  const params = {};
  for (const f of fields) {
    const v = state[f.name];
    if (f.kind === "dateRange" || f.kind === "numberRange") {
      const from = state[f.name + "__from"];
      const to = state[f.name + "__to"];
      if (from) params[f.fromParam] = from;
      if (to) params[f.toParam] = to;
      continue;
    }
    if (v !== undefined && v !== null && v !== "") {
      params[f.param || f.name] = v;
    }
  }
  return params;
}

export default function FilterBar({ fields, onApply }) {
  const [state, setState] = useState({});
  if (!fields || fields.length === 0) return null;

  const set = (k, v) => setState((s) => ({ ...s, [k]: v }));
  const apply = () => onApply(buildParams(fields, state));
  const clear = () => {
    setState({});
    onApply({});
  };

  return (
    <FlexBox
      style={{ gap: "0.75rem", padding: "0.25rem 0 0.5rem", flexWrap: "wrap", alignItems: "flex-end" }}
    >
      {fields.map((f) => {
        if (f.kind === "codeValue" || f.kind === "ref") {
          return (
            <div key={f.name} style={{ minWidth: "180px" }}>
              <Label>{f.label}</Label>
              <ComboField
                field={{ ...f, type: f.kind }}
                value={state[f.name] || ""}
                onChange={(v) => set(f.name, v)}
              />
            </div>
          );
        }
        if (f.kind === "dateRange") {
          return (
            <div key={f.name}>
              <Label>{f.label}</Label>
              <FlexBox style={{ gap: "0.35rem" }}>
                <Input type="Date" value={state[f.name + "__from"] || ""} onInput={(e) => set(f.name + "__from", e.target.value)} />
                <Input type="Date" value={state[f.name + "__to"] || ""} onInput={(e) => set(f.name + "__to", e.target.value)} />
              </FlexBox>
            </div>
          );
        }
        if (f.kind === "numberRange") {
          return (
            <div key={f.name}>
              <Label>{f.label}</Label>
              <FlexBox style={{ gap: "0.35rem" }}>
                <Input type="Number" placeholder="min" value={state[f.name + "__from"] || ""} onInput={(e) => set(f.name + "__from", e.target.value)} style={{ width: "90px" }} />
                <Input type="Number" placeholder="max" value={state[f.name + "__to"] || ""} onInput={(e) => set(f.name + "__to", e.target.value)} style={{ width: "90px" }} />
              </FlexBox>
            </div>
          );
        }
        // text
        return (
          <div key={f.name}>
            <Label>{f.label}</Label>
            <Input value={state[f.name] || ""} onInput={(e) => set(f.name, e.target.value)} />
          </div>
        );
      })}
      <Button design="Transparent" icon="filter" onClick={apply}>Filter</Button>
      <Button design="Transparent" icon="clear-filter" onClick={clear}>Clear</Button>
    </FlexBox>
  );
}