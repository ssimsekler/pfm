// Create a transaction linked to a Cash Flow Item (materialize). The resulting
// transaction inherits the item's expense category and cannot be split
// (Policy 1) — enforced server-side by POST /v1/recurring/materialize.
import { useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, TextField, Alert, Box,
} from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";
import { api } from "../api";
import ComboField from "./ComboField";

const ACCOUNT_FIELD = { type: "ref", refEntity: "accounts" };
const CCY_FIELD = { type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" };

export default function MaterializeDialog({ item, onClose, onDone }) {
  const [accountId, setAccountId] = useState("");
  const [dueDate, setDueDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [amount, setAmount] = useState(item?.expected_amount ?? "");
  const [currency, setCurrency] = useState(item?.currency || "");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!accountId) { setError("Select an account."); return; }
    setBusy(true); setError(null);
    try {
      await api.post("/v1/recurring/materialize", {
        cash_flow_item_id: item.uuid,
        account_id: accountId,
        due_date: dueDate,
        amount: amount === "" ? undefined : Number(amount),
        currency: currency || undefined,
      });
      onDone && onDone();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create transaction from “{item?.name}”</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        <Alert severity="info" sx={{ mb: 2 }}>
          The transaction inherits this item’s expense category and cannot be split (Policy 1).
        </Alert>
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <ComboField field={ACCOUNT_FIELD} value={accountId} onChange={setAccountId} label="Account" required />
          <DatePicker label="Transaction date" value={dueDate ? dayjs(dueDate) : null}
            onChange={(d) => setDueDate(d ? d.format("YYYY-MM-DD") : "")}
            slotProps={{ textField: { size: "small", fullWidth: true } }} />
          <TextField label="Amount" type="number" size="small" value={amount} onChange={(e) => setAmount(e.target.value)}
            helperText="Defaults to the item's expected amount if left blank" />
          <Box>
            <ComboField field={CCY_FIELD} value={currency} onChange={setCurrency} label="Currency" />
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={busy}>{busy ? "Creating…" : "Create transaction"}</Button>
      </DialogActions>
    </Dialog>
  );
}