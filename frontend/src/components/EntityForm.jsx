// Metadata-driven create/edit form (ADR #32, refined confirmation model).
//
// Confirmation policy:
//   - Save (create/update): NO confirmation (saves directly).
//   - Cancel: confirm ONLY if the form has unsaved changes (dirty).
//   - Delete is handled by EntityManager (always confirmed).
// The confirm dialog is a SIBLING of the form dialog (never nested) to avoid
// stacked modal overlays that block clicks (#1).
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
} from "@ui5/webcomponents-react";
import { api } from "../api";
import ComboField from "./ComboField";
import ConfirmDialog from "./ConfirmDialog";
import SplitEditor from "./SplitEditor";

// Proper singular titles (avoids "Categorie" from a naive /s$/ strip — #6).
const SINGULAR = {
  "Currencies": "Currency",
  "Countries": "Country",
  "Institutions": "Institution",
  "Accounts": "Account",
  "Partners": "Partner",
  "Beneficiaries": "Beneficiary",
  "Expense Categories": "Expense Category",
  "Cash Flow Items": "Cash Flow Item",
  "Investments": "Investment",
  "Loans": "Loan",
  "Installment Plans": "Installment Plan",
  "Goals": "Goal",
  "Budgets": "Budget",
  "Transactions": "Transaction",
  "LLM Providers": "LLM Provider",
  "Integration Endpoints": "Integration Endpoint",
  "Categorization Rules": "Categorization Rule",
  "Currency Rates": "Currency Rate",
  "Holiday Calendars": "Holiday Calendar",
  "Recurrence Profiles": "Recurrence Profile",
  "Users": "User",
};

function singular(title) {
  if (SINGULAR[title]) return SINGULAR[title];
  if (title.endsWith("ies")) return title.slice(0, -3) + "y";
  if (title.endsWith("s")) return title.slice(0, -1);
  return title;
}

function initialValues(fields, record) {
  const v = {};
  for (const f of fields) {
    let val = record ? record[f.name] : undefined;
    if (val === undefined || val === null) val = f.type === "boolean" ? false : "";
    if (f.type === "json" && val && typeof val === "object") {
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
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);

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

  const setField = (name, val) => {
    setDirty(true);
    setValues((v) => {
      const next = { ...v, [name]: val };
      // A.4: default the transaction name to the cash-flow item's name.
      if (cfg.hasSplits && name === "cash_flow_item_id" && val && !v.name) {
        // best-effort: look up the item name from the combo cache via API is async;
        // here we leave name empty if unknown — SplitEditor/ComboField handle labels.
      }
      return next;
    });
  };

  // A.4: when a cash-flow item is picked and name is empty, default it from the item.
  useEffect(() => {
    if (!cfg.hasSplits) return;
    const cfiId = values.cash_flow_item_id;
    if (!cfiId || values.name) return;
    let alive = true;
    api
      .get(`/v1/cash-flow-items/${cfiId}`)
      .then((item) => {
        if (alive && item && item.name) {
          setValues((v) => (v.name ? v : { ...v, name: item.name }));
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [cfg.hasSplits, values.cash_flow_item_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const setSplitsDirty = (rows) => {
    setDirty(true);
    setSplits(rows);
  };

  const renderField = (f) => {
    const val = values[f.name];
    if (f.type === "boolean") {
      return <Switch checked={Boolean(val)} onChange={(e) => setField(f.name, e.target.checked)} />;
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
      return <ComboField field={f} value={val} onChange={(v) => setField(f.name, v)} />;
    }
    return (
      <Input value={val ?? ""} onInput={(e) => setField(f.name, e.target.value)} style={{ width: "100%" }} />
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
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
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
      setDirty(false);
      onSaved && onSaved(saved);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function requestClose() {
    if (dirty) {
      setConfirmCancel(true);
    } else {
      onClose();
    }
  }

  return (
    <>
      <Dialog
        open
        resizable
        draggable
        headerText={`${isEdit ? "Edit" : "Create"} ${singular(cfg.title)}`}
        onAfterClose={requestClose}
        style={{ width: "640px", maxWidth: "95vw" }}
        footer={
          <Bar
            endContent={
              <>
                <Button design="Transparent" onClick={requestClose} disabled={busy}>Cancel</Button>
                <Button design="Emphasized" onClick={doSave} disabled={busy}>
                  {busy ? "Saving…" : "Save"}
                </Button>
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
              onChange={setSplitsDirty}
              disabled={splitsDisabled}
            />
          ) : null}
        </div>
      </Dialog>

      <ConfirmDialog
        open={confirmCancel}
        title="Discard changes?"
        message="You have unsaved changes. Discard them and close?"
        confirmText="Discard"
        confirmDesign="Negative"
        onConfirm={() => {
          setConfirmCancel(false);
          onClose();
        }}
        onCancel={() => setConfirmCancel(false)}
      />
    </>
  );
}
