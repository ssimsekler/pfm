// Value-help dropdown for form fields (ADR #32).
//
// Loads options from either a code list (type "codeValue" → listKey) or a
// referenced entity's list endpoint (type "ref" → refEntity), then renders a
// native <select> (reliable population + selection across all dialogs; the UI5
// ComboBox change/selection handling was unreliable and left lists empty — #11).
// Emits the selected option's id/code (or "" when cleared).
import { useEffect, useState } from "react";
import { api } from "../api";
import { ENTITIES } from "../entities";

// Module-level cache so repeated forms don't refetch the same lists.
const cache = new Map();

function cacheKey(field) {
  return field.type === "codeValue" ? `cv:${field.listKey}` : `ref:${field.refEntity}`;
}

async function loadOptions(field) {
  const key = cacheKey(field);
  if (cache.has(key)) return cache.get(key);

  let options = [];
  try {
    if (field.type === "codeValue") {
      const rows = await api.get(`/v1/code-lists/${field.listKey}/values`);
      options = (rows || []).map((r) => ({ value: r.uuid, label: r.label || r.code }));
    } else if (field.type === "ref") {
      const cfg = ENTITIES[field.refEntity];
      const path = cfg ? cfg.path : `/v1/${field.refEntity}`;
      const valueKey = field.refValue || "uuid";
      const labelKey = field.refLabel || "name";
      const data = await api.get(path, { limit: 500 });
      const items = Array.isArray(data) ? data : data.items || [];
      options = items.map((r) => ({
        value: r[valueKey],
        label: r[labelKey] != null ? String(r[labelKey]) : String(r[valueKey]),
      }));
    }
  } catch {
    options = [];
  }
  cache.set(key, options);
  return options;
}

export function clearComboCache() {
  cache.clear();
}

const selectStyle = {
  width: "100%",
  height: "2.25rem",
  padding: "0 0.5rem",
  border: "1px solid var(--sapField_BorderColor, #89919a)",
  borderRadius: "var(--sapField_BorderCornerRadius, 4px)",
  background: "var(--sapField_Background, #fff)",
  color: "var(--sapField_TextColor, #32363a)",
  font: "inherit",
};

export default function ComboField({ field, value, onChange, disabled }) {
  const [options, setOptions] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    setReady(false);
    loadOptions(field).then((opts) => {
      if (alive) {
        setOptions(opts);
        setReady(true);
      }
    });
    return () => {
      alive = false;
    };
  }, [field.type, field.listKey, field.refEntity]);

  return (
    <select
      value={value == null ? "" : String(value)}
      disabled={disabled || !ready}
      onChange={(e) => onChange(e.target.value)}
      style={selectStyle}
    >
      <option value="">{ready ? "— select —" : "Loading…"}</option>
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}