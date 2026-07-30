// Autocomplete combobox for value-help fields (ADR #32).
//
// Loads options from either a code list (type "codeValue" → listKey) or a
// referenced entity's list endpoint (type "ref" → refEntity). Falls back to a
// plain input if options can't be loaded. Emits the selected value's id/code.
import { useEffect, useState } from "react";
import { ComboBox, ComboBoxItem } from "@ui5/webcomponents-react";
import { api } from "../api";
import { ENTITIES } from "../entities";

// Simple module-level cache so repeated forms don't refetch the same lists.
const cache = new Map();

async function loadOptions(field) {
  const key =
    field.type === "codeValue"
      ? `cv:${field.listKey}`
      : `ref:${field.refEntity}`;
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

export default function ComboField({ field, value, onChange, disabled }) {
  const [options, setOptions] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
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

  // The visible text for the current value.
  const current = options.find((o) => String(o.value) === String(value));
  const text = current ? current.label : "";

  const handleChange = (e) => {
    const typed = e.target.value;
    const match = options.find((o) => o.label === typed);
    // If the typed text matches an option label, emit its value; otherwise clear.
    onChange(match ? match.value : "");
  };

  return (
    <ComboBox
      value={text}
      disabled={disabled || !ready}
      placeholder={ready ? "Type to search…" : "Loading…"}
      onChange={handleChange}
      style={{ width: "100%" }}
    >
      {options.map((o) => (
        <ComboBoxItem key={String(o.value)} text={o.label} />
      ))}
    </ComboBox>
  );
}