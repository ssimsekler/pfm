// Metadata-driven create/edit form (MUI). Confirmation model (ADR #38):
// no confirm on Save; confirm on Cancel only if dirty. Delete handled by manager.
import { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Switch,
  Alert,
  Box,
  FormHelperText,
  MenuItem,
  Typography,
} from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";
import { api } from "../api";
import { getDayjsDateFormat } from "../format";
import ComboField, { clearComboCache } from "./ComboField";
import ConfirmDialog from "./ConfirmDialog";
import SplitEditor from "./SplitEditor";

const SINGULAR = {
  Currencies: "Currency", Countries: "Country", Institutions: "Institution",
  Accounts: "Account", Partners: "Partner", Beneficiaries: "Beneficiary",
  "Expense Categories": "Expense Category", "Cash Flow Items": "Cash Flow Item",
  Investments: "Investment", Loans: "Loan", "Installment Plans": "Installment Plan",
  Goals: "Goal", Budgets: "Budget", Transactions: "Transaction",
  "LLM Providers": "LLM Provider", "Integration Endpoints": "Integration Endpoint",
  "Categorization Rules": "Categorization Rule", "Currency Rates": "Currency Rate",
  "Holiday Calendars": "Holiday Calendar", Users: "User",
};
function singular(t) {
  if (SINGULAR[t]) return SINGULAR[t];
  if (t.endsWith("ies")) return t.slice(0, -3) + "y";
  if (t.endsWith("s")) return t.slice(0, -1);
  return t;
}

// Batch 10: a credential picker backed by the Credentials Store (/v1/credentials).
// Selects by mnemonic_id. Optional `field.category` filters to a category_key.
function CredentialRefField({ field, value, onChange, label, required, disabled }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    let alive = true;
    api.get("/v1/credentials").then((all) => {
      if (!alive) return;
      const list = (all || []).filter(
        (c) => !field.category || c.category_key === field.category
      );
      setRows(list);
    }).catch(() => setRows([]));
    return () => { alive = false; };
  }, [field.category]);
  return (
    <TextField label={label} select value={value ?? ""} fullWidth size="small"
      required={required} disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      helperText={rows.length === 0 ? "No credentials yet — add one under Configuration → Credentials." : undefined}>
      <MenuItem value=""><em>None</em></MenuItem>
      {rows.map((c) => (
        <MenuItem key={c.mnemonic_id} value={c.mnemonic_id}>
          {c.name} ({c.category_key})
        </MenuItem>
      ))}
    </TextField>
  );
}

function initialValues(fields, record) {
  const v = {};
  for (const f of fields) {
    let val = record ? record[f.name] : undefined;
    if (val === undefined || val === null) val = f.type === "boolean" ? false : "";
    if (f.type === "json" && val && typeof val === "object") val = JSON.stringify(val, null, 2);
    v[f.name] = val;
  }
  return v;
}

export default function EntityForm({ entity, cfg, record, onClose, onSaved }) {
  const isEdit = Boolean(record);
  const idField = cfg.idField || "uuid";
  const [values, setValues] = useState(() => initialValues(cfg.fields, record));
  const [splits, setSplits] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  // Bump on open so Autocomplete option lists reload (new records show up) (#3).
  const [refreshToken] = useState(() => Date.now());

  const splitsDisabled = useMemo(
    () => cfg.hasSplits && Boolean(values.cash_flow_item_id),
    [cfg.hasSplits, values.cash_flow_item_id]
  );

  // Exclude self as its own parent for hierarchical entities (#3).
  const selfExclude = useMemo(() => {
    if (!isEdit) return undefined;
    const s = new Set();
    if (record && record[idField]) s.add(String(record[idField]));
    return s;
  }, [isEdit, record, idField]);

  useEffect(() => {
    if (cfg.hasSplits && isEdit && record[idField]) {
      api.get(`${cfg.path}/${record[idField]}/splits`).then((rows) =>
        setSplits((rows || []).map((r) => ({
          expense_category_id: r.expense_category_id || "",
          beneficiary_id: r.beneficiary_id || "",
          amount: r.amount,
        })))
      ).catch(() => setSplits([]));
    }
  }, [cfg.hasSplits, cfg.path, idField, isEdit, record]);

  const setField = (name, val) => {
    setDirty(true);
    setValues((v) => ({ ...v, [name]: val }));
  };

  // Default transaction name from selected cash-flow item (A.4).
  useEffect(() => {
    if (!cfg.hasSplits) return;
    const cfiId = values.cash_flow_item_id;
    if (!cfiId || values.name) return;
    let alive = true;
    api.get(`/v1/cash-flow-items/${cfiId}`).then((item) => {
      if (alive && item && item.name) setValues((v) => (v.name ? v : { ...v, name: item.name }));
    }).catch(() => {});
    return () => { alive = false; };
  }, [cfg.hasSplits, values.cash_flow_item_id]); // eslint-disable-line

  const setSplitsDirty = (rows) => { setDirty(true); setSplits(rows); };

  // A transaction is "item-linked" (Policy 1) when it carries a cash_flow_item_id.
  const itemLinked = useMemo(
    () => cfg.hasSplits && Boolean(values.cash_flow_item_id),
    [cfg.hasSplits, values.cash_flow_item_id]
  );

  const isDisabled = (f) => Boolean(f.disabled) || (f.lockWhenItemLinked && itemLinked);

  const renderField = (f) => {
    const val = values[f.name];
    const disabled = isDisabled(f);
    if (f.type === "boolean") {
      return (
        <FormControlLabel
          control={<Switch checked={Boolean(val)} disabled={disabled} onChange={(e) => setField(f.name, e.target.checked)} />}
          label={f.label}
        />
      );
    }
    if (f.type === "textarea" || f.type === "json") {
      return (
        <TextField label={f.label} value={val ?? ""} onChange={(e) => setField(f.name, e.target.value)}
          fullWidth size="small" multiline minRows={f.type === "json" ? 4 : 2} required={f.required} disabled={disabled} />
      );
    }
    if (f.type === "date") {
      return (
        <DatePicker
          label={f.label}
          value={val ? dayjs(val) : null}
          disabled={disabled}
          // Item 4: honor the resolved date format and allow the open-ended
          // sentinel 9999-12-31 (no false "error" red border).
          format={getDayjsDateFormat()}
          maxDate={dayjs("9999-12-31")}
          onChange={(d) => setField(f.name, d ? d.format("YYYY-MM-DD") : "")}
          slotProps={{ textField: { size: "small", fullWidth: true, required: f.required } }}
        />
      );
    }
    if (f.type === "number") {
      return (
        <TextField label={f.label} type="number" value={val ?? ""} onChange={(e) => setField(f.name, e.target.value)}
          fullWidth size="small" required={f.required} disabled={disabled} />
      );
    }
    if (f.type === "select") {
      return (
        <TextField label={f.label} select value={val ?? ""} onChange={(e) => setField(f.name, e.target.value)}
          fullWidth size="small" required={f.required} disabled={disabled}>
          <MenuItem value=""><em>None</em></MenuItem>
          {(f.options || []).map((o) => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
        </TextField>
      );
    }
    if (f.type === "credentialRef") {
      // Batch 10: pick a Credentials Store entry (by mnemonic_id). Optionally
      // filter to a category via f.category (e.g. "llm_provider").
      return (
        <CredentialRefField field={f} value={val} onChange={(v) => setField(f.name, v)}
          label={f.label} required={f.required} disabled={disabled} />
      );
    }
    if (f.type === "codeValue" || f.type === "ref") {
      const exclude = f.refEntity === entity ? selfExclude : undefined;
      return (
        <ComboField field={f} value={val} onChange={(v) => setField(f.name, v)}
          label={f.label} required={f.required} exclude={exclude} refreshToken={refreshToken} disabled={disabled} />
      );
    }
    return (
      <TextField label={f.label} value={val ?? ""} onChange={(e) => setField(f.name, e.target.value)}
        fullWidth size="small" required={f.required} disabled={disabled} />
    );
  };

  function validate() {
    for (const f of cfg.fields) {
      if (f.required) {
        const v = values[f.name];
        if (v === "" || v === null || v === undefined) return `${f.label} is required.`;
      }
    }
    if (cfg.hasSplits && !splitsDisabled && splits.length > 0) {
      const total = splits.reduce((s, r) => s + (Number(r.amount) || 0), 0);
      const target = Number(values.amount) || 0;
      if (Math.abs(target - total) > 0.00005) return `Split lines must sum to the amount (${target}); got ${total}.`;
      for (const r of splits) {
        if (!r.expense_category_id) return "Each split line needs a category.";
        if (!r.amount) return "Each split line needs an amount.";
      }
    }
    return null;
  }

  function buildPayload() {
    const out = {};
    for (const f of cfg.fields) {
      let v = values[f.name];
      if (f.type === "boolean") { out[f.name] = Boolean(v); continue; }
      if (v === "" || v === null || v === undefined) { if (isEdit) out[f.name] = null; continue; }
      if (f.type === "number") v = Number(v);
      if (f.type === "json") { try { v = JSON.parse(v); } catch { v = null; } }
      out[f.name] = v;
    }
    return out;
  }

  async function doSave() {
    const v = validate();
    if (v) { setError(v); return; }
    setBusy(true); setError(null);
    try {
      const payload = buildPayload();
      let saved;
      if (isEdit) saved = await api.patch(`${cfg.path}/${record[idField]}`, payload);
      else saved = await api.post(cfg.path, payload);
      // Only sync splits when the editor is enabled AND there is something to
      // write (or we're clearing an edit that previously had splits). Avoids an
      // unnecessary PUT for plain transactions.
      if (cfg.hasSplits && !splitsDisabled) {
        const clean = splits.filter((r) => r.expense_category_id && r.amount !== "")
          .map((r) => ({ expense_category_id: r.expense_category_id, beneficiary_id: r.beneficiary_id || null, amount: Number(r.amount) }));
        const hadSplits = Boolean(record?.is_split);
        if (clean.length > 0 || hadSplits) {
          const txnId = (saved && saved[idField]) || record?.[idField];
          if (txnId) await api.put(`${cfg.path}/${txnId}/splits`, { splits: clean });
        }
      }
      // Invalidate this entity's option cache so other forms see the new record (#3).
      clearComboCache({ type: "ref", refEntity: entity });
      setDirty(false);
      onSaved && onSaved(saved);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function requestClose() {
    if (dirty) setConfirmCancel(true);
    else onClose();
  }

  return (
    <>
      <Dialog open onClose={requestClose} maxWidth="md" fullWidth>
        <DialogTitle>{`${isEdit ? "Edit" : "Create"} ${singular(cfg.title)}`}</DialogTitle>
        <DialogContent dividers>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          {/* Batch 10: group fields into titled sections. A field's optional
              `section` label buckets it; ungrouped fields render first. This lets
              e.g. the Account dialog place all the bank/identifier numbers in
              their own "Bank / identifiers" section. */}
          {(() => {
            const groups = [];
            const byLabel = new Map();
            for (const f of cfg.fields) {
              const label = f.section || "";
              if (!byLabel.has(label)) {
                const g = { label, fields: [] };
                byLabel.set(label, g);
                groups.push(g);
              }
              byLabel.get(label).fields.push(f);
            }
            // Keep the default (unlabeled) group first, then the rest in order.
            groups.sort((a, b) => (a.label === "" ? -1 : b.label === "" ? 1 : 0));
            return groups.map((g, gi) => (
              <Box key={g.label || "_default"} sx={{ mt: gi === 0 ? 0.5 : 2 }}>
                {g.label ? (
                  <Typography variant="subtitle2" color="text.secondary"
                    sx={{ mb: 1, mt: 1, borderTop: 1, borderColor: "divider", pt: 1.5 }}>
                    {g.label}
                  </Typography>
                ) : null}
                <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
                  {g.fields.map((f) => {
                    const full = f.type === "textarea" || f.type === "json";
                    return (
                      <Box key={f.name} sx={{ gridColumn: full ? "1 / -1" : "auto" }}>
                        {renderField(f)}
                        {f.help ? <FormHelperText>{f.help}</FormHelperText> : null}
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            ));
          })()}
          {cfg.hasSplits ? (
            <SplitEditor amount={values.amount} rows={splits} onChange={setSplitsDirty} disabled={splitsDisabled} />
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={requestClose} disabled={busy}>Cancel</Button>
          <Button onClick={doSave} variant="contained" disabled={busy}>{busy ? "Saving…" : "Save"}</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={confirmCancel}
        title="Discard changes?"
        message="You have unsaved changes. Discard them and close?"
        confirmText="Discard"
        confirmColor="error"
        onConfirm={() => { setConfirmCancel(false); onClose(); }}
        onCancel={() => setConfirmCancel(false)}
      />
    </>
  );
}
