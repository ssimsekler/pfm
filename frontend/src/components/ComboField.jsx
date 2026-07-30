// Autocomplete value-help (MUI). Type-ahead over a code list (type "codeValue")
// or a referenced entity (type "ref"). Emits the selected id/code (or "").
//
// Fixes from feedback: friendly type-ahead (#2); a module cache that can be
// cleared after writes so new records appear without a page refresh (#3); and an
// optional `exclude` set to hide ids (e.g. the record itself as its own parent, #3).
import { useEffect, useMemo, useState } from "react";
import { Autocomplete, TextField } from "@mui/material";
import { api } from "../api";
import { ENTITIES } from "../entities";

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

// Clear cached option lists (call after create/edit/delete so lists refresh).
export function clearComboCache(field) {
  if (field) cache.delete(cacheKey(field));
  else cache.clear();
}

export default function ComboField({
  field,
  value,
  onChange,
  disabled,
  label,
  required,
  exclude,
  refreshToken,
}) {
  const [options, setOptions] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    setReady(false);
    // refreshToken change forces a fresh load (bypasses cache).
    if (refreshToken) clearComboCache(field);
    loadOptions(field).then((opts) => {
      if (alive) {
        setOptions(opts);
        setReady(true);
      }
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [field.type, field.listKey, field.refEntity, refreshToken]);

  const visible = useMemo(() => {
    if (!exclude || exclude.size === 0) return options;
    return options.filter((o) => !exclude.has(String(o.value)));
  }, [options, exclude]);

  const selected = visible.find((o) => String(o.value) === String(value)) || null;

  return (
    <Autocomplete
      options={visible}
      value={selected}
      getOptionLabel={(o) => (o && o.label != null ? o.label : "")}
      isOptionEqualToValue={(o, v) => String(o.value) === String(v.value)}
      onChange={(_e, opt) => onChange(opt ? opt.value : "")}
      disabled={disabled || !ready}
      fullWidth
      size="small"
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          required={required}
          placeholder={ready ? "Type to search…" : "Loading…"}
        />
      )}
    />
  );
}