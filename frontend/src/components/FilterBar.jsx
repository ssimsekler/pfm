// Structured filter bar (MUI) for list screens (#20). Emits query params merged
// into the DataGrid request. Date ranges use real date pickers (#4).
import { useState } from "react";
import { Box, Button, TextField, Paper } from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";
import ComboField from "./ComboField";

function buildParams(fields, state) {
  const params = {};
  for (const f of fields) {
    if (f.kind === "dateRange" || f.kind === "numberRange") {
      const from = state[f.name + "__from"];
      const to = state[f.name + "__to"];
      if (from) params[f.fromParam] = from;
      if (to) params[f.toParam] = to;
      continue;
    }
    const v = state[f.name];
    if (v !== undefined && v !== null && v !== "") params[f.param || f.name] = v;
  }
  return params;
}

export default function FilterBar({ fields, onApply }) {
  const [state, setState] = useState({});
  if (!fields || fields.length === 0) return null;
  const set = (k, v) => setState((s) => ({ ...s, [k]: v }));

  return (
    <Paper variant="outlined" sx={{ p: 1.5, mb: 2 }}>
      <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap", alignItems: "center" }}>
        {fields.map((f) => {
          if (f.kind === "codeValue" || f.kind === "ref") {
            return (
              <Box key={f.name} sx={{ minWidth: 200 }}>
                <ComboField field={{ ...f, type: f.kind }} value={state[f.name] || ""} onChange={(v) => set(f.name, v)} label={f.label} />
              </Box>
            );
          }
          if (f.kind === "dateRange") {
            return (
              <Box key={f.name} sx={{ display: "flex", gap: 1 }}>
                <DatePicker label={`${f.label} from`} value={state[f.name + "__from"] ? dayjs(state[f.name + "__from"]) : null}
                  onChange={(d) => set(f.name + "__from", d ? d.format("YYYY-MM-DD") : "")}
                  slotProps={{ textField: { size: "small" } }} />
                <DatePicker label={`${f.label} to`} value={state[f.name + "__to"] ? dayjs(state[f.name + "__to"]) : null}
                  onChange={(d) => set(f.name + "__to", d ? d.format("YYYY-MM-DD") : "")}
                  slotProps={{ textField: { size: "small" } }} />
              </Box>
            );
          }
          if (f.kind === "numberRange") {
            return (
              <Box key={f.name} sx={{ display: "flex", gap: 1 }}>
                <TextField label={`${f.label} min`} type="number" size="small" value={state[f.name + "__from"] || ""} onChange={(e) => set(f.name + "__from", e.target.value)} sx={{ width: 120 }} />
                <TextField label={`${f.label} max`} type="number" size="small" value={state[f.name + "__to"] || ""} onChange={(e) => set(f.name + "__to", e.target.value)} sx={{ width: 120 }} />
              </Box>
            );
          }
          return (
            <TextField key={f.name} label={f.label} size="small" value={state[f.name] || ""} onChange={(e) => set(f.name, e.target.value)} />
          );
        })}
        <Button variant="contained" startIcon={<FilterAltIcon />} onClick={() => onApply(buildParams(fields, state))}>Filter</Button>
        <Button startIcon={<FilterAltOffIcon />} onClick={() => { setState({}); onApply({}); }}>Clear</Button>
      </Box>
    </Paper>
  );
}