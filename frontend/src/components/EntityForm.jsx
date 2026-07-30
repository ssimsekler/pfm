// Metadata-driven create/edit form (ADR #32). Confirms before every save.
//
// Renders inputs from an entity's `fields`. On save: POST (create) or PATCH
// (edit, changed fields only). For transactions (hasSplits), embeds SplitEditor
// and persists split lines via PUT /v1/transactions/{id}/splits.
import { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  Bar,
  Button,
  Label,
  Input,
  TextArea,
  Switch,
  DatePicker,
  MessageStrip,
  Title,
} from "@ui5/webcomponents-react";
import { api } from "../api";
import ComboField from "./ComboField";
import ConfirmDialog from "./ConfirmDialog";
import SplitEditor from "./SplitEditor";

function initialValues(fields, record) {
  const v = {};
  for (const f of fields) {
    let val = record ? record[f.name] : undefined;
    if (val === undefined || val === null) val = f.type === "boolean" ? false : "";
    if ((f.type === "json") && val && typeof val === "object") {
      val = JSON.stringify(val, null, 2);
    }
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
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const splitsDisabled = useMemo(
    () => cfg.hasSplits && Boolean(values.cash_flow_item_id),
    [cfg.hasSplits, values.cash_flow_item_id]
  );

  // Load existing splits when editing a transaction.
  useEffect(() => {
    if (cfg.hasSplits && isEdit && record[idField]) {
      api
        .get(`${cfg.path}/${record[idField]}/splits`)
        .then((rows) =>
          setSplits(
            (rows || []).map((r) => ({
              expense_category_id: r.expense_category_id || "",
              beneficiary_id: r.beneficiary_id || "",
              amount: r.amount,
            }))
          )
        )
        .catch(() => setSplits([]));
    }
  }, [cfg.hasSplits, cfg.path, idField, isEdit, record]);

  const setField = (name, val) => setValues((v) => ({ ...v, [name]: val }));

  const renderField = (f) => {
    const val = values[f.name];
    if (f.type === "boolean") {
      return (
        <Switch checked={Boolean(val)} onChange={(e) => setField(f.name, e.target.checked)} />
      );
    }
    if (f.type === "textarea" || f.type === "json") {
      return (
        <TextArea
          value={val ?? ""}
          rows={f.type === "json" ? 4 : 2}
          onInput={(e) => setField(f.name, e.target.value)}
          style={{ width: "100%" }}
        />
      );
    }
    if (f.type === "date") {
      return (
        <DatePicker
          value={val ?? ""}
          formatPattern="yyyy-MM-dd"
          onChange={(e) => setField(f.name, e.detail.value)}
          style={{ width: "100%" }}
        />
      );
    }
    if (f.type === "number") {
      return (
        <Input
          type="Number"
          value={String(val ?? "")}
          onInput={(e) => setField(f.name, e.target.value)}
          style={{ width: "100%" }}
        />
      );
    }
    if (f.type === "codeValue" || f.type === "ref") {
      return (
        <ComboField field={f} value={val} onChange={(v) => setField(f.name, v)} />
      );
    }
    // default text
    return (
      <Input
        value={val ?? ""}
        onInput={(e) => setField(f.name, e.target.value)}
        style={{ width: "100%" }}
      />
    );
  };

  function validate() {
    for (const f of cfg.fields) {
      if (f.required) {
        const v = values[f.name];
        if (v === "" || v === null || v === undefined) {
          return `${f.label} is required.`;
        }
      }
    }
    if (cfg.hasSplits && !splitsDisabled && splits.length > 0) {
      const total = splits.reduce((s, r) => s + (Number(r.amount) || 0), 0);
      const target = Number(values.amount) || 0;
      if (Math.abs(target - total) > 0.00005) {
        return `Split lines must sum to the amount (${target}); got ${total}.`;
      }
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
      if (f.type === "boolean") {
        out[f.name] = Boolean(v);
        continue;
      }
      if (v === "" || v === null || v === undefined) {
        // Skip empties on create; send null on edit to clear optionals.
        if (isEdit) out[f.name] = null;
        continue;
      }
      if (f.type === "number") v = Number(v);
      if (f.type === "json") {
        try {
          v = JSON.parse(v);
        } catch {
          v = null;
        }
      }
      out[f.name] = v;
    }
    return out;
  }

  async function doSave() {
    setBusy(true);
    setError(null);
    try {
      const payload = buildPayload();
      let saved;
      if (isEdit) {
        saved = await api.patch(`${cfg.path}/${record[idField]}`, payload);
      } else {
        saved = await api.post(cfg.path, payload);
      }
      // Persist splits for transactions (unless disabled by Policy 1).
      if (cfg.hasSplits && !splitsDisabled) {
        const txnId = (saved && saved[idField]) || record?.[idField];
        if (txnId) {
          const clean = splits
            .filter((r) => r.expense_category_id && r.amount !== "")
            .map((r) => ({
              expense_category_id: r.expense_category_id,
              beneficiary_id: r.beneficiary_id || null,
              amount: Number(r.amount),
            }));
          await api.put(`${cfg.path}/${txnId}/splits`, { splits: clean });
        }
      }
      setConfirmOpen(false);
      onSaved && onSaved(saved);
    } catch (e) {
      setConfirmOpen(false);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function requestSave() {
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setError(null);
    setConfirmOpen(true);
  }

  return (
    <Dialog
      open
      headerText={`${isEdit ? "Edit" : "Create"} ${cfg.title.replace(/s$/, "")}`}
      onAfterClose={onClose}
      style={{ width: "640px", maxWidth: "95vw" }}
      footer={
        <Bar
          endContent={
            <>
              <Button design="Transparent" onClick={onClose}>Cancel</Button>
              <Button design="Emphasized" onClick={requestSave}>Save</Button>
            </>
          }
        />
      }
    >
      <div style={{ padding: "0.5rem 0.25rem" }}>
        {error ? (
          <MessageStrip design="Negative" hideCloseButton style={{ marginBottom: "0.75rem" }}>
            {error}
          </MessageStrip>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem 1rem" }}>
          {cfg.fields.map((f) => {
            const fullRow = f.type === "textarea" || f.type === "json";
            return (
              <div key={f.name} style={{ gridColumn: fullRow ? "1 / -1" : "auto" }}>
                <Label showColon required={f.required}>{f.label}</Label>
                <div style={{ marginTop: "0.15rem" }}>{renderField(f)}</div>
                {f.help ? (
                  <Label style={{ color: "var(--sapNeutralTextColor)", fontSize: "0.75rem" }}>
                    {f.help}
                  </Label>
                ) : null}
              </div>
            );
          })}
        </div>

        {cfg.hasSplits ? (
          <SplitEditor
            amount={values.amount}
            rows={splits}
            onChange={setSplits}
            disabled={splitsDisabled}
          />
        ) : null}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title={isEdit ? "Save changes?" : "Create record?"}
        message={
          isEdit
            ? "Do you want to save the changes to this record?"
            : "Do you want to create this record?"
        }
        confirmText="Save"
        busy={busy}
        onConfirm={doSave}
        onCancel={() => setConfirmOpen(false)}
      />
    </Dialog>
  );
}