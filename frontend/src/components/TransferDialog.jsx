// Transfer dialog (A.5): move money between two accounts, creating a dual-leg
// transfer (two linked transactions + a transfer_group) via POST /v1/transfers.
// Supports cross-currency (enter the received amount on the other side).
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

export default function TransferDialog({ onClose, onDone }) {
  const [form, setForm] = useState({
    name: "Transfer",
    from_account_id: "",
    to_account_id: "",
    from_amount: "",
    to_amount: "",
    from_currency: "",
    to_currency: "",
    txn_date: dayjs().format("YYYY-MM-DD"),
    note: "",
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const setE = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const crossCcy = form.from_currency && form.to_currency && form.from_currency !== form.to_currency;

  async function submit() {
    if (!form.from_account_id || !form.to_account_id) { setError("Select both accounts."); return; }
    if (form.from_account_id === form.to_account_id) { setError("From and to accounts must differ."); return; }
    if (!form.from_amount) { setError("Enter an amount."); return; }
    setBusy(true); setError(null);
    try {
      await api.post("/v1/transfers", {
        name: form.name || "Transfer",
        from_account_id: form.from_account_id,
        to_account_id: form.to_account_id,
        from_amount: Number(form.from_amount),
        to_amount: form.to_amount === "" ? undefined : Number(form.to_amount),
        from_currency: form.from_currency,
        to_currency: form.to_currency || form.from_currency,
        txn_date: form.txn_date,
        note: form.note || undefined,
      });
      onDone && onDone();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>New transfer</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <TextField label="Name" size="small" value={form.name} onChange={setE("name")} />
          <ComboField field={ACCOUNT_FIELD} value={form.from_account_id} onChange={set("from_account_id")} label="From account" required />
          <ComboField field={ACCOUNT_FIELD} value={form.to_account_id} onChange={set("to_account_id")} label="To account" required />
          <Stack direction="row" spacing={2}>
            <TextField label="Amount sent" type="number" size="small" value={form.from_amount}
              onChange={setE("from_amount")} sx={{ flex: 1 }} />
            <Box sx={{ width: 140 }}>
              <ComboField field={CCY_FIELD} value={form.from_currency} onChange={set("from_currency")} label="From ccy" />
            </Box>
          </Stack>
          <Stack direction="row" spacing={2}>
            <TextField label="Amount received" type="number" size="small" value={form.to_amount}
              onChange={setE("to_amount")} sx={{ flex: 1 }}
              helperText={crossCcy ? "Cross-currency: enter received amount" : "Defaults to amount sent"} />
            <Box sx={{ width: 140 }}>
              <ComboField field={CCY_FIELD} value={form.to_currency} onChange={set("to_currency")} label="To ccy" />
            </Box>
          </Stack>
          <DatePicker label="Date" value={form.txn_date ? dayjs(form.txn_date) : null}
            onChange={(d) => set("txn_date")(d ? d.format("YYYY-MM-DD") : "")}
            slotProps={{ textField: { size: "small", fullWidth: true } }} />
          <TextField label="Note" size="small" value={form.note} onChange={setE("note")} multiline minRows={2} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={busy}>{busy ? "Creating…" : "Create transfer"}</Button>
      </DialogActions>
    </Dialog>
  );
}