// Multi-line transaction split editor (ADR #33).
//
// Manages an array of split rows { expense_category_id, beneficiary_id, amount }.
// Shows the running total and "remaining" against the transaction amount; the
// parent saves them via PUT /v1/transactions/{id}/splits (must sum exactly).
import {
  Button,
  Label,
  Input,
  Text,
  Title,
  MessageStrip,
  FlexBox,
} from "@ui5/webcomponents-react";
import ComboField from "./ComboField";

const CATEGORY_FIELD = {
  type: "ref",
  refEntity: "expense-categories",
};
const BENEFICIARY_FIELD = {
  type: "ref",
  refEntity: "beneficiaries",
};

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

export default function SplitEditor({ amount, rows, onChange, disabled }) {
  const total = rows.reduce((s, r) => s + toNum(r.amount), 0);
  const target = toNum(amount);
  const remaining = Number((target - total).toFixed(4));
  const balanced = Math.abs(remaining) < 0.00005;

  const update = (idx, patch) => {
    const next = rows.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    onChange(next);
  };
  const addRow = () =>
    onChange([...rows, { expense_category_id: "", beneficiary_id: "", amount: "" }]);
  const removeRow = (idx) => onChange(rows.filter((_, i) => i !== idx));

  return (
    <div style={{ marginTop: "1rem", borderTop: "1px solid var(--sapList_BorderColor,#e5e5e5)", paddingTop: "0.75rem" }}>
      <FlexBox style={{ justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <Title level="H5">Split lines</Title>
        <Button icon="add" design="Transparent" onClick={addRow} disabled={disabled}>
          Add line
        </Button>
      </FlexBox>

      {disabled ? (
        <MessageStrip design="Information" hideCloseButton style={{ marginBottom: "0.5rem" }}>
          Splitting is disabled when a Cash Flow Item is linked (Policy 1).
        </MessageStrip>
      ) : null}

      {rows.length === 0 ? (
        <Text style={{ color: "var(--sapNeutralTextColor)" }}>No split lines.</Text>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "0.25rem 0.5rem" }}><Label>Category</Label></th>
              <th style={{ textAlign: "left", padding: "0.25rem 0.5rem" }}><Label>Beneficiary</Label></th>
              <th style={{ textAlign: "left", padding: "0.25rem 0.5rem", width: "140px" }}><Label>Amount</Label></th>
              <th style={{ width: "48px" }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={idx}>
                <td style={{ padding: "0.25rem 0.5rem" }}>
                  <ComboField
                    field={CATEGORY_FIELD}
                    value={r.expense_category_id}
                    onChange={(v) => update(idx, { expense_category_id: v })}
                    disabled={disabled}
                  />
                </td>
                <td style={{ padding: "0.25rem 0.5rem" }}>
                  <ComboField
                    field={BENEFICIARY_FIELD}
                    value={r.beneficiary_id}
                    onChange={(v) => update(idx, { beneficiary_id: v })}
                    disabled={disabled}
                  />
                </td>
                <td style={{ padding: "0.25rem 0.5rem" }}>
                  <Input
                    type="Number"
                    value={String(r.amount ?? "")}
                    onInput={(e) => update(idx, { amount: e.target.value })}
                    disabled={disabled}
                    style={{ width: "100%" }}
                  />
                </td>
                <td style={{ padding: "0.25rem 0.5rem", textAlign: "center" }}>
                  <Button
                    icon="delete"
                    design="Transparent"
                    onClick={() => removeRow(idx)}
                    disabled={disabled}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <FlexBox style={{ justifyContent: "flex-end", gap: "1.5rem", marginTop: "0.5rem" }}>
        <Text>Total: {total.toFixed(2)}</Text>
        <Text style={{ color: balanced ? "var(--sapPositiveTextColor)" : "var(--sapNegativeTextColor)" }}>
          Remaining: {remaining.toFixed(2)}
        </Text>
      </FlexBox>

      {!balanced && rows.length > 0 ? (
        <MessageStrip design="Warning" hideCloseButton style={{ marginTop: "0.5rem" }}>
          Split lines must sum exactly to the transaction amount ({target.toFixed(2)}) before saving.
        </MessageStrip>
      ) : null}
    </div>
  );
}